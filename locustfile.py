import random

from locust import TaskSet, task, between, HttpLocust

USERS_AMOUNT = 100
readers_per_reviewer = 3
do_pushback = False
assignment_slice_seconds = 10
intermediate_save_probability = 0.05
skip_probability = 0.05


class LocustMixin:
    host = 'http://localhost:5000'
    # wait_time = between(0.001, 0.001)
    wait_time = between(4, 5)


class AbstractUserTaskSet(TaskSet):
    headers = None
    tasks_per_request = 4
    logs_name = ''

    def on_start(self):
        self.login()

    def login(self):
        email, password = self.credentials.pop()
        response = self.client.post("/auth/obtain-token", json={"email": email, "password": password})
        token = response.json()["token"]
        self.headers = {'Authorization': f'Bearer {token}'}

    @task(5)
    def recycle(self):
        url = "/task/request"
        data = {"amount": self.tasks_per_request, "includeCurrentTasks": True}
        self.client.post(url, json=data, headers=self.headers, name=f"{self.logs_name} outdated {url}")
        self._sleep(assignment_slice_seconds + 1)

    @task(100)
    def accomplish_tasks(self):
        url = "/task/request"
        data = {"amount": self.tasks_per_request, "includeCurrentTasks": True}
        with self.client.post(url, json=data, headers=self.headers, name=f"{self.logs_name} {url}", catch_response=True) as response:
            tasks = response.json()['tasks']
            if len(tasks) > 0:
                response.success()
            else:
                response.failure("Task list is empty")
        for t in tasks:
            self.finish_task(t)

    def finish_task(self, task):
        id = task['taskId']
        result = self.get_result(task)
        choice = random.choices(
            [0, 1, 2],
            [skip_probability, intermediate_save_probability, 1 - skip_probability - intermediate_save_probability]
        )[0]
        if choice == 0 and task['isSkippable']:
            self.client.post(f"/task/{id}/skip", headers=self.headers, name=f"{self.logs_name} /task/skip")
            return
        if choice == 1:
            data = {"final": False, "result": result, "timeSpent": 1}
            self.client.post(f"/task/{id}/save", json=data, headers=self.headers, name=f"{self.logs_name} /task/save")
        data = {"final": True, "result": result, "timeSpent": 2}
        self.client.post(f"/task/{id}/save", json=data, headers=self.headers, name=f"{self.logs_name} /task/submit")


class ReaderTaskSet(AbstractUserTaskSet):
    credentials = []
    logs_name = 'reader'

    def setup(self):
        reader_credentials = [(f"user_{i}@gmail.com", "password") for i in range(USERS_AMOUNT)]
        self.credentials.clear()
        self.credentials.extend(reader_credentials)

    def get_result(self, task):
        is_pushback = bool(task['previousSubmission'])
        return task['taskData'] if is_pushback else {'coin': "HEAD" if random.random() < 0.5 else "TAIL"}


class ReviewerTaskSet(AbstractUserTaskSet):
    credentials = []
    logs_name = 'reviewer'

    def setup(self):
        reviewer_credentials = [(f"reviewer_{i}@gmail.com", "password") for i in range(USERS_AMOUNT)]
        self.credentials.clear()
        self.credentials.extend(reviewer_credentials)

    def get_result(self, task):
        task_data = task['taskData']
        is_rejectable = task_data['isRejectable']
        inspected_task = task_data['inspectedTask']
        if do_pushback and is_rejectable and random.random() < 0.10:
            return {"decision": "reject", "feedback": {}}
        return {"decision": "approve", "data": inspected_task}


class ReaderUser(LocustMixin, HttpLocust):
    weight = readers_per_reviewer
    task_set = ReaderTaskSet


class ReviewerUser(LocustMixin, HttpLocust):
    weight = 1
    task_set = ReviewerTaskSet

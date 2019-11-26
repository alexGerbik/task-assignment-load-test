import random

from locust import TaskSet, task, between, HttpLocust

USERS_AMOUNT = 100
host = 'http://localhost:5000'

reader_credentials = []

reviewer_credentials = []

# wait_time = between(0.001, 0.001)
wait_time = between(4, 5)


def login(task_set, creds):
    email, password = creds.pop()
    response = task_set.client.post("/auth/obtain-token", json={"email": email, "password": password})
    token = response.json()["token"]
    task_set.headers = {'Authorization': f'Bearer {token}'}


class ReaderTaskSet(TaskSet):
    headers = None

    def setup(self):
        global reader_credentials
        reader_credentials = [(f"user_{i}@gmail.com", "password") for i in range(USERS_AMOUNT)]


    def on_start(self):
        login(self, reader_credentials)

    @task
    def annotate(self):
        with self.client.post("/task/request", json={"amount": 1, "includeCurrentTasks": True},
                                    headers=self.headers, name="/task/request reader", catch_response=True) as response:
            tasks = response.json()['tasks']
            if len(tasks) > 0:
                response.success()
            else:
                response.failure("Task list is empty")
        for t in tasks:
            self._finish_task(t)

    def _finish_task(self, task):
        id = task['taskId']
        is_pushback = bool(task['previousSubmission'])
        result = task['taskData'] if is_pushback else {'coin': "HEAD" if random.random() < 0.5 else "TAIL"}
        self.client.post(f"/task/{id}/save", json={"final": True, "result": result, "timeSpent": 1},
                         headers=self.headers, name="/task/save reader")


class Reader(HttpLocust):
    weight = 3
    # weight = 1
    host = host
    task_set = ReaderTaskSet
    wait_time = wait_time


class ReviewerTaskSet(TaskSet):
    headers = None

    def setup(self):
        global reviewer_credentials
        reviewer_credentials = [(f"reviewer_{i}@gmail.com", "password") for i in range(USERS_AMOUNT)]

    def on_start(self):
        login(self, reviewer_credentials)

    @task
    def review(self):
        with self.client.post("/task/request", json={"amount": 1, "includeCurrentTasks": True},
                                    headers=self.headers, name="/task/request reviewer", catch_response=True) as response:
            tasks = response.json()['tasks']
            if len(tasks) > 0:
                response.success()
            else:
                response.failure("Task list is empty")
        for t in tasks:
            # print(t)
            id = t['taskId']
            task_data = t['taskData']
            self._finish_task(id, task_data)

    def _finish_task(self, id, task_data):
        is_rejectable = task_data['isRejectable']
        inspected_task = task_data['inspectedTask']

        # if is_rejectable and random.random() < 0.10:
        #     result = {"decision": "reject", "feedback": {}}
        # else:
        result = {"decision": "approve", "data": inspected_task}

        self.client.post(f"/task/{id}/save", json={"final": True, "result": result, "timeSpent": 1},
                         headers=self.headers, name="/task/save reviewer")




class ReviewerUser(HttpLocust):
    weight = 1
    host = host
    task_set = ReviewerTaskSet
    wait_time = wait_time

import random

from locust import TaskSet, task, between, HttpLocust

USERS_AMOUNT = 100
host = 'http://localhost:5000'

reader_credentials = [(f"user_{i}@gmail.com", "password") for i in range(USERS_AMOUNT)]

# reviewer_credentials = [(f"reviewer_{i}@gmail.com", "password") for i in range(USERS_AMOUNT)]
reviewer_credentials = [("reviewer@gmail.com", "password")]


def login(task_set, creds):
    email, password = creds.pop()
    response = task_set.client.post("/auth/obtain-token", json={"email": email, "password": password})
    token = response.json()["token"]
    task_set.headers = {'Authorization': f'Bearer {token}'}


class ReaderTaskSet(TaskSet):
    headers = None

    def on_start(self):
        login(self, reader_credentials)

    @task
    def annotate(self):
        response = self.client.post("/task/request", json={"amount": 1, "includeCurrentTasks": True}, headers=self.headers)
        tasks = response.json()['tasks']
        for t in tasks:
            id = t['taskId']
            self._finish_task(id)

    def _finish_task(self, id):
        result = {'coin': "HEAD" if random.random() < 0.5 else "TAIL"}
        self.client.post(f"/task/{id}/save", json={"final": True, "result": result, "timeSpent": 1},
                         headers=self.headers, name="/task/[id]/save")


# class Reader(HttpLocust):
#     host = host
#     task_set = ReaderTaskSet
#     wait_time = between(1, 2)




class ReviewerTaskSet(TaskSet):
    headers = None

    def on_start(self):
        login(self, reviewer_credentials)

    @task
    def review(self):
        response = self.client.post("/task/request", json={"amount": 1, "includeCurrentTasks": True},
                                    headers=self.headers)
        tasks = response.json()['tasks']
        for t in tasks:
            print(t)
            id = t['taskId']
            task_data = t['taskData']
            self._finish_task(id, task_data)

    def _finish_task(self, id, task_data):
        is_rejectable = task_data['isRejectable']
        annotations = task_data['annotations']
        inspected_task = task_data['inspectedTask']

        result = None
        if is_rejectable and len(annotations) == 1:
            ann = next(iter(annotations.values()))
            if ann != inspected_task:
                result = {"decision": "reject", "feedback": {}}
        if not result:
            result = {"decision": "approve", "data": inspected_task}

        self.client.post(f"/task/{id}/save", json={"final": True, "result": result, "timeSpent": 1},
                         headers=self.headers, name="/task/[id]/save")




class ReviewerUser(HttpLocust):
    host = host
    task_set = ReviewerTaskSet
    wait_time = between(1, 2)
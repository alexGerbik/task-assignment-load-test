import random

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from locust import TaskSet, task, between, HttpLocust

USERS_AMOUNT = 100
readers_per_reviewer = 3
do_pushback = False
assignment_slice_seconds = 10
intermediate_save_probability = 0.05
skip_probability = 0.05


def load_pem_private_key(private_key_filename):
    with open(private_key_filename, "rb") as file:
        data = file.read()
    return serialization.load_pem_private_key(data, password=None, backend=default_backend())


def load_users(amount, filename):
    with open(filename) as file:
        ids = file.read().splitlines()
    ids = ids[:amount]
    import uuid

    return [uuid.UUID(i) for i in ids]


def create_token(user_id, permissions, private_key):
    payload = {"userId": str(user_id), "permissions": permissions}
    headers = {"authServiceId": "main"}
    return jwt.encode(payload, private_key, algorithm="RS256", headers=headers).decode("utf-8")


private_key = load_pem_private_key('key.pem')


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
        jwt_token = self.credentials.pop()
        response = self.client.post("/auth/get-session-token", headers={"Authorization": f'Bearer {jwt_token}'})
        token = response.json()["token"]
        self.headers = {'Authorization': f'Session {token}'}

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
        reader_credentials = load_users(USERS_AMOUNT, 'users.txt')
        reader_credentials = [create_token(c, ['tas:annotator'], private_key) for c in reader_credentials]
        self.credentials.clear()
        self.credentials.extend(reader_credentials)

    def get_result(self, task):
        is_pushback = bool(task['previousSubmission'])
        return task['taskData'] if is_pushback else {'coin': "HEAD" if random.random() < 0.5 else "TAIL"}


class ReviewerTaskSet(AbstractUserTaskSet):
    credentials = []
    logs_name = 'reviewer'

    def setup(self):
        reviewer_credentials = load_users(USERS_AMOUNT, 'reviewers.txt')
        reviewer_credentials = [create_token(c, ['tas:annotator'], private_key) for c in reviewer_credentials]
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

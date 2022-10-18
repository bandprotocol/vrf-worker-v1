import datetime
import json
from typing import Type
from google.cloud.tasks_v2 import CloudTasksClient, HttpMethod
from google.protobuf import duration_pb2, timestamp_pb2
from .config import AppEnvConfig


class CreateTask:
    """The class contains a method to create a new task on GCP Cloud Tasks."""

    def __init__(self, _config: Type[AppEnvConfig]) -> None:
        """Sets config from AppEnvConfig class.

        Args:
            _config (Type[AppEnvConfig]): Class AppEnvConfig
        """
        self.config = _config

    def create_new_task(self) -> None:
        """Creates a new task on Cloud Tasks.

        Constructs the task with the environment variables input and sends the
        transaction to Cloud Tasks to create a new task in the queue.
        """
        # Create a client.
        client = CloudTasksClient()

        project = self.config.PROJECT
        queue = self.config.QUEUE
        location = self.config.LOCATION
        url = self.config.CLOUD_RUN_URL
        payload = None
        in_seconds = self.config.IN_SECONDS
        task_name = None
        deadline = self.config.DEADLINE
        audience = self.config.AUDIENCE
        service_account_email = self.config.SERVICE_ACCOUNT_DETAIL

        # Construct the fully qualified queue name.
        parent = client.queue_path(project, location, queue)

        # Construct the request body.
        task = {
            "http_request": {  # Specify the type of request.
                "http_method": HttpMethod.POST,
                "url": url,  # The full url path that the task will be sent to.
                "oidc_token": {
                    "service_account_email": service_account_email,
                    "audience": audience,
                },
            }
        }

        if payload is not None:
            if isinstance(payload, dict):
                # Convert dict to JSON string
                payload = json.dumps(payload)
                # specify http content-type to application/json
                task["http_request"]["headers"] = {"Content-type": "application/json"}

            # The API expects a payload of type bytes.
            converted_payload = payload.encode()

            # Add the payload to the request.
            task["http_request"]["body"] = converted_payload

        if in_seconds is not None:
            # Convert "seconds from now" into an rfc3339 datetime string.
            d = datetime.datetime.utcnow() + datetime.timedelta(seconds=in_seconds)

            # Create Timestamp protobuf.
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(d)

            # Add the timestamp to the tasks.
            task["schedule_time"] = timestamp

        if task_name is not None:
            # Add the name to tasks.
            task["name"] = client.task_path(project, location, queue, task_name)

        if deadline is not None:
            # Add dispatch deadline for requests sent to the worker.
            duration = duration_pb2.Duration()
            duration.FromSeconds(deadline)
            task["dispatch_deadline"] = duration

        # Use the client to build and send the task.
        response = client.create_task(request={"parent": parent, "task": task})

        print("Created task {}".format(response.name))

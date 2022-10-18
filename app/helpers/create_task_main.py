from .config import CreateTaskConfig
from .create_task import CreateTask

if __name__ == "__main__":
    create_task = CreateTask(CreateTaskConfig)
    create_task.create_new_task()

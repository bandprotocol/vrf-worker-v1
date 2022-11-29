from typing import List
from dataclasses import dataclass
from flask import Flask
from flask_sqlalchemy import SQLAlchemy


@dataclass
class Task:
    nonce: int
    is_resolve: bool
    time: int
    caller: str
    task_fee: str
    seed: str
    client_seed: str
    resolved_block_height: int
    fork_checked: bool


class Database(SQLAlchemy):
    """Database integrated with SQLAlchemy."""

    def __init__(self, app: Flask):
        super().__init__(app)
        self.__init_model()

    def __init_model(self):
        db = self

        class ProviderTasks(db.Model):
            """VRF request tasks from the VRF Provider contract."""

            nonce = db.Column(db.Integer, primary_key=True, nullable=False)
            is_resolve = db.Column(db.Boolean, nullable=False, default=False)
            time = db.Column(db.Integer, nullable=False)
            caller = db.Column(db.String, nullable=False)
            task_fee = db.Column(db.String, nullable=False)
            seed = db.Column(db.String, nullable=False)
            client_seed = db.Column(db.String, nullable=False)
            resolved_block_height = db.Column(db.Integer, nullable=True)
            fork_checked = db.Column(db.Boolean, nullable=False, default=False)

            __tablename__ = "provider_tasks"

        db.Index(f"provider_tasks_index", ProviderTasks.nonce, ProviderTasks.time)

        self.ProviderTasks = ProviderTasks

        class ErrorCount(db.Model):
            item = db.Column(db.Integer, primary_key=True, nullable=False)
            error_count = db.Column(db.Integer, nullable=False)
            __tablename__ = "error_count"

        self.ErrorCount = ErrorCount

    def get_latest_task_by_nonce(self) -> Task:
        """Retrieves the nonce of the latest task from the database.

        Returns:
            Task: Nonce of the latest task.
        """
        try:
            return self.session.query(self.ProviderTasks).order_by(self.ProviderTasks.nonce.desc()).first()

        except Exception as e:
            print("Error get_latest_task_by_nonce:", e)
            raise

    def get_unresolved_tasks(self, offset: int, limit: int) -> List[Task]:
        """Retrieves the unresolved tasks from the database.

        Args:
            offset (int): The task number to start query.
            limit (int): Number of tasks to query.

        Returns:
            List[Task]: A list of unresolved tasks.
        """
        try:
            return (
                self.session.query(self.ProviderTasks)
                .filter_by(is_resolve=False)
                .order_by(self.ProviderTasks.nonce.asc())
                .offset(offset)
                .limit(limit)
                .all()
            )

        except Exception as e:
            print("Error get_unresolved_tasks:", e)
            raise

    def add_new_task_if_not_existed(self, new_task: Task, current_block: int) -> None:
        """Adds a new task to the database if it does not previously existed.

        Args:
            new_task (Task): The new task to be added.
            current_block (int): Current block number.
        """
        try:
            task = self.session.query(self.ProviderTasks).filter_by(nonce=new_task.nonce).one_or_none()
            if task is None:
                if new_task.is_resolve:
                    self.session.add(
                        self.ProviderTasks(
                            nonce=new_task.nonce,
                            is_resolve=new_task.is_resolve,
                            time=new_task.time,
                            caller=new_task.caller,
                            task_fee=str(new_task.task_fee),
                            seed=new_task.seed,
                            client_seed=new_task.client_seed,
                            resolved_block_height=current_block,
                            fork_checked=False,
                        )
                    )
                else:
                    self.session.add(
                        self.ProviderTasks(
                            nonce=new_task.nonce,
                            is_resolve=new_task.is_resolve,
                            time=new_task.time,
                            caller=new_task.caller,
                            task_fee=str(new_task.task_fee),
                            seed=new_task.seed,
                            client_seed=new_task.client_seed,
                            resolved_block_height=None,
                            fork_checked=False,
                        )
                    )

        except Exception as e:
            print("Error add_new_task_if_not_existed:", e)
            raise

    def resolve_task(self, nonce: int, block_height: int) -> None:
        """Marks a task on the database as resolved.

        Filters a task from the database from the input nonce. Marks the task
        as resolved and records the input block height as the resolved block
        number.

        Args:
            nonce (int): Task's nonce to mark resolved.
            block_height (int): Block number that the task is marked as
            resolved.
        """
        try:
            task = self.session.query(self.ProviderTasks).filter_by(nonce=nonce).first()
            task.is_resolve = True
            task.resolved_block_height = block_height

        except Exception as e:
            print(f"Error resolve_task - task {nonce}:", e)
            raise

    def get_tasks_to_fork_check(self, current_block: int, offset: int, limit: int, block_diff: int) -> List[Task]:
        """Retrieves a list of tasks to be checked for chain fork.

        Args:
            current_block (int): Current block number.
            offset (int): The task number to start query.
            limit (int): Number of tasks to query.

        Returns:
            List[Task]: A list of tasks to be checked for chain fork.
        """
        try:
            return (
                self.session.query(self.ProviderTasks)
                .filter_by(fork_checked=False)
                .filter(self.ProviderTasks.resolved_block_height < current_block - block_diff)
                .order_by(self.ProviderTasks.nonce.asc())
                .offset(offset)
                .limit(limit)
                .all()
            )

        except Exception as e:
            print("Error get_tasks_to_fork_check:", e)
            raise

    def delete_task(self, task_nonce: int) -> None:
        """Delete a task with the input nonce from the database.

        Args:
            task_nonce (int): Task nonce.
        """
        try:
            self.session.query(self.ProviderTasks).filter_by(nonce=task_nonce).delete()

        except Exception as e:
            print("Error delete_task:", e)
            raise

    def delete_multiple_tasks(self, task_nonce: int) -> None:
        """Delete multiple tasks from the database.

        Filters all the tasks with nonce greater than the input nonce and
        deletes them from the database.

        Args:
            task_nonce (int): Task nonce.
        """
        try:
            self.session.query(self.ProviderTasks).filter(self.ProviderTasks.nonce >= task_nonce).delete()

        except Exception as e:
            print("Error delete_multiple_tasks:", e)
            raise

    def replace_task_in_db(self, task_nonce: int, new_task: Task, current_block: int) -> None:
        """Replaces a task on the database with a new task.

        Args:
            task_nonce (int): Task nonce to be replaced.
            new_task (Task): New task for replacement.
            current_block (int): Current block number.
        """
        try:
            task = self.session.query(self.ProviderTasks).filter_by(nonce=task_nonce).first()
            task.is_resolve = new_task.is_resolve
            task.time = new_task.time
            task.caller = new_task.caller
            task.task_fee = str(new_task.task_fee)
            task.seed = new_task.seed
            task.client_seed = new_task.client_seed
            if new_task.is_resolve:
                task.resolved_block_height = current_block
            task.fork_checked = False

        except Exception as e:
            print("Error replace_task_in_db:", e)
            raise

    def mark_not_resolve(self, task_nonce: int) -> None:
        """Marks a task with the input nonce unresolved.

        Args:
            task_nonce (int): Task nonce.
        """
        try:
            task = self.session.query(self.ProviderTasks).filter_by(nonce=task_nonce).first()
            task.is_resolve = False
            task.resolved_block_height = None

        except Exception as e:
            print("Error mark_not_resolve:", e)
            raise

    def fork_check_mark_done(self, task_nonce: int) -> None:
        """Marks a task with the input nonce as fork checked.

        Args:
            task_nonce (int): Task nonce.
        """
        try:
            task = self.session.query(self.ProviderTasks).filter_by(nonce=task_nonce).first()
            task.fork_checked = True

        except Exception as e:
            print("Error fork_check_complete:", e)
            raise

    def get_error_count(self) -> int:
        """Retrieves the error count.

        Returns:
            int: error count
        """
        try:
            item = self.session.query(self.ErrorCount).one_or_none()
            if item is None:
                return 0

            return item.error_count

        except Exception as e:
            print("Error get_error_count:", e)
            raise

    def change_error_count(self, new_error_count: int) -> None:
        """Updates the error count

        Args:
            new_error_count (int): New error count
        """
        try:
            item = self.session.query(self.ErrorCount).one_or_none()
            if item is None:
                self.session.add(self.ErrorCount(error_count=0))
                item = self.session.query(self.ErrorCount).one_or_none()

            item.error_count = new_error_count
        except Exception as e:
            print("Error update_error_count:", e)
            raise

from boto.swf.exceptions import SWFResponseError, SWFTypeAlreadyExistsError


class RemoteTaskSpec(object):
    def __init__(self, name, version, task_factory=None):
        self._name = str(name)
        self._version = str(version)
        self._task_factory = None
        if task_factory is not None:
            self.bind_task_factory(task_factory)

    def bind_task_factory(self, task_factory):
        if not callable(task_factory):
            raise ValueError('the task factory must be callable')
        self._task_factory = task_factory

    def register(self, poller):
        successfuly_registered_remote = self._register_remote()
        if not successfuly_registered_remote:
            return False
        self._register_with_poller(poller)
        return True

    def _register_with_poller(self, poller):
        if self._task_factory is None:
            raise RuntimeError(
                '%s is not bound to a task_factory' % self.__class__
            )
        poller.register(
            name=self._name,
            version=self._version,
            task_factory=self._task_factory
        )

    def _register_remote(self):
        success = True
        registered_as_new = self._try_register_remote()
        if not registered_as_new:
            success = self._check_if_compatible()
        return success

    def _try_register_remote(self):
        raise NotImplementedError

    def _check_if_compatible(self):
        raise NotImplementedError


class AWSActivitySpec(RemoteTaskSpec):
    def __init__(self, domain, name, version, task_list, client,
                 heartbeat=60,
                 schedule_to_close=420,
                 schedule_to_start=120,
                 start_to_close=300,
                 description=None,
                 task_factory=None):
        super(AWSActivitySpec, self).__init__(name, version, task_factory)
        self._domain = str(domain)
        self._task_list = str(task_list)
        self._client = client
        self._heartbeat = str(heartbeat)
        self._schedule_to_close = str(schedule_to_close)
        self._schedule_to_start = str(schedule_to_start)
        self._start_to_close = str(start_to_close)
        self._description = None
        if description is not None:
            self._description = str(description)

    def _try_register_remote(self):
        try:
            self._client.register_activity_type(
                domain=self._domain,
                name=self._name,
                version=self._version,
                task_list=self._task_list,
                default_task_heartbeat_timeout=self._heartbeat,
                default_task_schedule_to_close_timeout=self._schedule_to_close,
                default_task_schedule_to_start_timeout=self._schedule_to_start,
                default_task_start_to_close_timeout=self._start_to_close,
                description=self._description
            )
        except SWFResponseError:  # SWFTypeAlreadyExistsError is subclass
            return False
        return True

    def _check_if_compatible(self):
        try:
            c = self._client.describe_activity_type(
                domain=self._domain,
                activity_name=self._name,
                activity_version=self._version
            )['configuration']
        except SWFResponseError:
            return False
        return all([
            c['defaultTaskList']['name'] == self._task_list,
            c['defaultTaskHeartbeatTimeout'] == self._heartbeat,
            c['defaultTaskScheduleToCloseTimeout'] == self._schedule_to_close,
            c['defaultTaskScheduleToStartTimeout'] == self._schedule_to_start,
            c['defaultTaskStartToCloseTimeout'] == self._start_to_close
        ])


class AWSWorkflowSpec(RemoteTaskSpec):
    def __init__(self, domain, name, version, task_list, client,
                 workflow_duration=3600,
                 decision_duration=60,
                 child_policy='TERMINATE',
                 description=None,
                 task_factory=None):
        super(AWSWorkflowSpec, self).__init__(name, version, task_factory)
        self._domain = str(domain)
        self._task_list = str(task_list)
        self._client = client
        self._workflow_duration = str(workflow_duration)
        self._decision_duration = str(decision_duration)
        self._child_policy = str(child_policy)
        self._description = None
        if description is not None:
            self._description = str(description)

    def _register_remote(self):
        try:
            workflow_duration = self._workflow_duration
            self._client.register_workflow_type(
                domain=self._domain,
                name=self._name,
                version=self._version,
                task_list=self._task_list,
                default_execution_start_to_close_timeout=workflow_duration,
                default_task_start_to_close_timeout=self._decision_duration,
                default_child_policy=self._child_policy,
                description=self._description
            )
        except SWFResponseError:
            return False
        return True

    def _check_if_compatible(self):
        try:
            c = self._client.describe_workflow_type(
                domain=self._domain,
                activity_name=self._name,
                activity_version=self._version
            )['configuration']
        except SWFResponseError:
            return False
        workflow_duration = self._workflow_duration
        return all([
            c['defaultTaskList']['name'] == self._task_list,
            c['defaultExecutionStartToCloseTimeout'] == workflow_duration,
            c['defaultTaskStartToCloseTimeout'] == self._decision_duration,
            c['defaultChildPolicy'] == self._child_policy
        ])

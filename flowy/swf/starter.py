import uuid
from contextlib import contextmanager

from boto.swf.exceptions import SWFResponseError
from flowy import logger, posint_or_none, str_or_none
from flowy.task import serialize_args


class WorkflowStarter(object):
    def __init__(self, name, version, client,
                 task_list=None,
                 decision_duration=None,
                 workflow_duration=None):
        self._name = str(name)
        self._version = str(version)
        self._client = client
        self._task_list = str_or_none(task_list)
        self._decision_duration = str_or_none(
            posint_or_none(decision_duration)
        )
        self._workflow_duration = str_or_none(
            posint_or_none(workflow_duration)
        )
        self._options = {'id': None, 'tags': None}

    def __call__(self, *args, **kwargs):
        workflow_id = self._id
        if workflow_id is None:
            workflow_id = uuid.uuid4()
        tags = self._tags
        if tags is not None:
            tags = sorted(tags)
        try:
            r = self._client.start_workflow_execution(
                workflow_id=str(workflow_id),
                workflow_name=self._name,
                workflow_version=self._version,
                task_list=self._task_list,
                input=self._serialize_arguments(*args, **kwargs),
                execution_start_to_close_timeout=self._workflow_duration,
                task_start_to_close_timeout=self._decision_duration,
                tag_list=tags,
            )
        except SWFResponseError:
            logger.exception('Could not start the workflow:')
            return None
        return r['runId']

    @property
    def _id(self):
        return self._options['id']

    @property
    def _tags(self):
        return self._options['tags']

    @contextmanager
    def id(self, id):
        old_options = self._options
        self._options = dict(self._options, id=id)
        yield
        self._options = old_options

    @contextmanager
    def tags(self, tags):
        tags = set(map(str, tags))
        if self._tags is not None:
            tags |= self._tags
        if len(tags) > 5:
            raise ValueError("Can't set more than 5 tags.")
        old_options = self._options
        self._options = dict(old_options, tags=tags)
        yield
        self._options = old_options

    _serialize_arguments = serialize_args

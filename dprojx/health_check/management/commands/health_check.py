import sys

from django.core.management.base import BaseCommand
import copy
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings

HEALTH_CHECK = getattr(settings, 'HEALTH_CHECK', {})
HEALTH_CHECK.setdefault('DISK_USAGE_MAX', 90)
HEALTH_CHECK.setdefault('MEMORY_MIN', 100)
HEALTH_CHECK.setdefault('WARNINGS_AS_ERRORS', True)

from django.utils.translation import gettext_lazy as _  # noqa: N812


class HealthCheckException(Exception):
    message_type = _("unknown error")

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "%s: %s" % (self.message_type, self.message)


class ServiceWarning(HealthCheckException):
    """
    Warning of service misbehavior.

    If the ``HEALTH_CHECK['WARNINGS_AS_ERRORS']`` is set to ``False``,
    these exceptions will not case a 500 status response.
    """

    message_type = _("warning")


class ServiceUnavailable(HealthCheckException):
    message_type = _("unavailable")


class ServiceReturnedUnexpectedResult(HealthCheckException):
    message_type = _("unexpected result")


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class HealthCheckPluginDirectory:
    """Django health check registry."""

    def __init__(self):
        self._registry = []  # plugin_class class -> plugin options

    def reset(self):
        """Reset registry state, e.g. for testing purposes."""
        self._registry = []

    def register(self, plugin, **options):
        """Add the given plugin from the registry."""
        # Instantiate the admin class to save in the registry
        self._registry.append((plugin, options))


plugin_dir = HealthCheckPluginDirectory()


class CheckMixin:
    _errors = None
    _plugins = None

    @property
    def errors(self):
        if not self._errors:
            self._errors = self.run_check()
        return self._errors

    @property
    def plugins(self):
        if not self._plugins:
            self._plugins = sorted((
                plugin_class(**copy.deepcopy(options))
                for plugin_class, options in plugin_dir._registry
            ), key=lambda plugin: plugin.identifier())
        return self._plugins

    def run_check(self):
        errors = []

        def _run(plugin):
            plugin.run_check()
            try:
                return plugin
            finally:
                from django.db import connections
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(self.plugins) or 1) as executor:
            for plugin in executor.map(_run, self.plugins):
                if plugin.critical_service:
                    if not HEALTH_CHECK['WARNINGS_AS_ERRORS']:
                        errors.extend(
                            e for e in plugin.errors
                            if not isinstance(e, ServiceWarning)
                        )
                    else:
                        errors.extend(plugin.errors)

        return errors


class Command(CheckMixin, BaseCommand):
    help = "Run health checks and exit 0 if everything went well."

    def handle(self, *args, **options):
        # perform all checks
        errors = self.errors

        for plugin in self.plugins:
            style_func = self.style.SUCCESS if not plugin.errors else self.style.ERROR
            self.stdout.write(
                "{:<24} ... {}\n".format(
                    plugin.identifier(),
                    style_func(plugin.pretty_status())
                )
            )

        if errors:
            sys.exit(1)

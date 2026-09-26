"""CraftyProse test suite.

Run from the repository root:  python -m unittest discover -s tests -t .

The suite must never need the network or the API (decision D9). Importing this
package replaces socket connections with an error, so an accidental network call
fails the test that made it instead of silently reaching out.
"""
import socket


class NetworkAccessError(RuntimeError):
    pass


def _refuse(*_args, **_kwargs):
    raise NetworkAccessError("network access is not allowed in the CraftyProse test suite")


class _GuardedSocket(socket.socket):
    def connect(self, *args, **kwargs):  # noqa: D401 - same signature as socket.connect
        _refuse()

    def connect_ex(self, *args, **kwargs):
        _refuse()


socket.socket = _GuardedSocket  # type: ignore[misc]
socket.create_connection = _refuse  # type: ignore[assignment]

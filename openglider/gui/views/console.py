from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import openglider
from openglider.gui.qt import QtCore
from qasync import QEventLoop
from qtconsole.inprocess import (QtInProcessKernelClient,
                                 QtInProcessKernelManager)
from qtconsole.rich_jupyter_widget import RichJupyterWidget

if TYPE_CHECKING:
    from openglider.gui.app.main_window import MainWindow

import asyncio

logging.getLogger("openglider")


class OpenGliderKernel(QtInProcessKernelClient):
    loop: QEventLoop = None

    def _dispatch_to_kernel(self, msg: str) -> None:
        """Send a message to the kernel and handle a reply."""
        kernel = self.kernel
        if kernel is None:
            raise RuntimeError("Cannot send request. No kernel exists.")

        stream = kernel.shell_stream
        self.session.send(stream, msg)
        msg_parts = stream.recv_multipart()

        asyncio.ensure_future(self.async_dispatch(msg_parts))
    
    async def async_dispatch(self, msg_parts: list[str]) -> None:
        await self.kernel.dispatch_shell(msg_parts)
        idents, reply_msg = self.session.recv(self.kernel.shell_stream, copy=False)
        self.shell_channel.call_handlers_later(reply_msg)

class OpenGliderKernelManager(QtInProcessKernelManager):
    client_class = "openglider.gui.views.console.OpenGliderKernel"

class ConsoleWidget(RichJupyterWidget):
    """
    Convenience class for a live IPython console widget.
    We can replace the standard banner using the customBanner argument
    """

    def __init__(self, app: MainWindow, customBanner: Any=None, *args: Any, **kwargs: Any):

        super().__init__(*args, **kwargs)
        self.app = app
        self.kernel_manager = OpenGliderKernelManager()
        self.kernel_manager.start_kernel()

        self.kernel_manager.kernel.gui = 'qt'
        self.kernel_client = kernel_client = self.kernel_manager.client()
        kernel_client.loop = app.app.loop
        #kernel_client.start_channels(shell=False, iopub=False, stdin=False, hb=False)
        kernel_client.start_channels()

        self.set_default_style("linux")
        self.font_size = 6
        self.gui_completion = 'droplist'

        self.push_local_ns("app", self.app)
        self.push_local_ns("openglider", openglider)
    
    def _complete(self) -> None:
        code = self.input_buffer

        # TODO: check what happens on autocompletion
        if code.startswith("app"):
            cursor_pos = self._get_input_buffer_cursor_pos()
            msg_id = self.kernel_client.complete(code=code, cursor_pos=cursor_pos)
            info = self._CompletionRequest(msg_id, code, cursor_pos)
            self._request_info['complete'] = info

            print(msg_id)
            return
        return super()._complete()

    def push_local_ns(self, name: str, value: Any) -> None:
        """
        Given a dictionary containing name / value pairs, push those variables
        to the IPython console widget
        """
        if self.kernel_manager.kernel is not None:
            self.kernel_manager.kernel.shell.push({name: value})

    def clear(self) -> None:
        """
        Clears the terminal
        """
        self._control.clear()

        # self.kernel_manager

    def print_text(self, text: str) -> None:
        """
        Prints some plain text to the console
        """
        self.append_stream(text)
        self._scroll_to_end()
        #self._append_plain_text(text)

    def execute_command(self, command: str) -> None:
        """
        Execute a command in the frame of the console widget
        """
        self._execute(command, False)
    
    def log_message(self, message: str) -> None:
        self.print_text(message + '\n')


class QSignaler(QtCore.QObject):
    log_message = QtCore.Signal(str)


class ConsoleHandler(logging.Handler):
    emitter = QtCore.Signal(str)
    """Logging handler to emit to LoggingConsole"""

    def __init__(self, console: ConsoleWidget, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.console = console
        self.signal = QSignaler()

        # make it thread safe
        self.signal.log_message.connect(self.console.log_message)

        self.setFormatter(logging.Formatter(
            fmt="{asctime} {levelname} ({name}): {message}",
            datefmt="%H:%M:%S",
            style="{"
            ))
        
        self.add_logger("openglider")
        #self.add_logger("gpufem")
    
    def add_logger(self, name: str) -> None:
        logger = logging.getLogger(name)
        logger.addHandler(self)

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < 20:
            return

        msg = self.format(record)
        self.signal.log_message.emit(msg)

        
        self.console.log_message(msg)

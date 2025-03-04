from openglider.gui.qt import QtWidgets
import vtkmodules
import vtkmodules.vtkRenderingOpenGL2
import vtkmodules.vtkRenderingCore
import vtkmodules.qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor
from vtkmodules.vtkRenderingCore import vtkActor

from openglider.gui.views_3d.interactor import Interactor


class View3D(QtWidgets.QWidget):
    show_axes = True
    renderer: vtkmodules.vtkRenderingCore.vtkRenderer

    def __init__(self, parent: QtWidgets.QWidget=None) -> None:
        super().__init__(parent)
        self.setLayout(QtWidgets.QHBoxLayout(self))

        self.frame = QtWidgets.QFrame()
        self.frame.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.frame)
        
        self.renderer = vtkmodules.vtkRenderingCore.vtkRenderer()

        # enable SSAO
        self.renderer.UseSSAOOn()
        self.renderer.SetSSAORadius(0.2)
        self.renderer.SetSSAOKernelSize(256)
        self.renderer.SetSSAOBlur(False)

        self.renderer.SetBackground(.2, .3, .4)
        self.renderer.SetViewport(0, 0, 1, 1)

        self.VTKRenderWindow = vtkmodules.vtkRenderingCore.vtkRenderWindow()

        self.VTKRenderWindow.AddRenderer(self.renderer)

        self.VTKRenderWindowInteractor = QVTKRenderWindowInteractor(self.frame, rw=self.VTKRenderWindow)
        self.frame.layout().addWidget(self.VTKRenderWindowInteractor)

        self.VTKCamera = vtkmodules.vtkRenderingCore.vtkCamera()
        self.VTKCamera.SetClippingRange(0.1, 1000)
        self.VTKCamera.SetFocalPoint(0, 0, -3)
        self.VTKCamera.SetPosition(-15, 0, -3)
        self.VTKCamera.SetRoll(90)
        self.renderer.SetActiveCamera(self.VTKCamera)

        self.VTKRenderWindowInteractor.SetInteractorStyle(Interactor())

        self.VTKRenderWindowInteractor.Initialize()
        #self.VTKRenderWindowInteractor.Start()
        #self.VTKRenderWindowInteractor.ReInitialize()

        self.axes = vtkAxesActor()
        self.clear()

    def clear(self) -> None:
        self.renderer.RemoveAllViewProps()
        if self.show_axes:
            self.show_actor(self.axes)  # type: ignore
        self.rerender()

    def show_actor(self, actor: vtkActor) -> None:
        self.renderer.AddActor(actor)
        self.VTKRenderWindow.Render()

    def rerender(self) -> None:
        self.VTKRenderWindow.Render()



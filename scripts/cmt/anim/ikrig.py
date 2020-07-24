from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import maya.cmds as cmds
import cmt.shortcuts as shortcuts

import logging
import os
import re
import webbrowser

from maya.app.general.mayaMixin import MayaQWidgetBaseMixin

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
import cmt.shortcuts as shortcuts

from cmt.ui.widgets.mayanodewidget import MayaNodeWidget
from cmt.ui.widgets.filepathwidget import FilePathWidget
from cmt.io.fbx import import_fbx

logger = logging.getLogger(__name__)

_win = None


class Parts(object):
    hips = 0
    chest = 1
    neck = 2
    head = 3
    left_clavicle = 4
    left_shoulder = 5
    left_elbow = 6
    left_hand = 7
    left_up_leg = 8
    left_lo_leg = 9
    left_foot = 10
    right_clavicle = 11
    right_shoulder = 12
    right_elbow = 13
    right_hand = 14
    right_up_leg = 15
    right_lo_leg = 16
    right_foot = 17

    def __init__(self):
        parts = [x for x in dir(Parts) if re.search("^(?!next)[a-zA-Z]\w*", x)]
        self.parts = [(p, getattr(Parts, p)) for p in parts]
        self.parts.sort(key=lambda x: x[1])
        self.current = 0

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        if self.current < len(self.parts):
            part = self.parts[self.current][0]
            self.current = self.current + 1
            return part
        else:
            raise StopIteration()


def attach_skeletons(source_joints, target_joints):
    """Create the ikRig node and constrain the target joints to locators driven by the ikRig node.

    :param source_joints: List of source joints in the order listed in Parts
    :param target_joints: List of target joints in the order listed in Parts
    :return: The created ikRig node
    """
    cmds.loadPlugin("cmt", qt=True)
    node = cmds.createNode("ikRig")
    locs = []
    for i, j in enumerate(source_joints):
        cmds.connectAttr(
            "{}.worldMatrix[0]".format(j), "{}.inMatrix[{}]".format(node, i)
        )
        path = shortcuts.get_dag_path2(j)
        rest_matrix = list(path.inclusiveMatrix())
        cmds.setAttr("{}.inRestMatrix[{}]".format(node, i), *rest_matrix, type="matrix")

        path = shortcuts.get_dag_path2(target_joints[i])
        matrix = list(path.inclusiveMatrix())
        cmds.setAttr("{}.targetRestMatrix[{}]".format(node, i), *matrix, type="matrix")

        loc = cmds.spaceLocator(name="ikrig_{}".format(target_joints[i]))[0]
        cmds.connectAttr("{}.outputTranslate[{}]".format(node, i), "{}.t".format(loc))
        cmds.connectAttr("{}.outputRotate[{}]".format(node, i), "{}.r".format(loc))

        cmds.setAttr("{}Shape.localScale".format(loc), 5, 5, 5)
        locs.append(loc)

    for loc, joint in zip(locs, target_joints):
        cmds.parentConstraint(loc, joint)
    loc = cmds.spaceLocator(name="rootMotion")[0]
    cmds.connectAttr("{}.rootMotion".format(node), "{}.opm".format(loc))
    return node


def show():
    """Shows the browser window."""
    global _win
    if _win:
        _win.close()
    _win = IKRigWindow()
    _win.show()


def documentation():
    pass
    # webbrowser.open("https://github.com/chadmv/cmt/wiki/Unit-Test-Runner-Dialog")


class IKRigWindow(MayaQWidgetBaseMixin, QMainWindow):
    def __init__(self, *args, **kwargs):
        super(IKRigWindow, self).__init__(*args, **kwargs)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("IK Rig")
        self.resize(1000, 600)

        widget = QWidget()
        self.setCentralWidget(widget)
        vbox = QVBoxLayout(widget)

        scroll = QScrollArea()
        vbox.addWidget(scroll)

        splitter = QSplitter(orientation=Qt.Horizontal)

        source_widget = QWidget()
        splitter.addWidget(source_widget)
        layout = QVBoxLayout(source_widget)
        label = QLabel("Source")
        font = label.font()
        font.setPointSize(18.0)
        label.setFont(font)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.source = SkeletonDefinitionWidget("source", self)
        layout.addWidget(self.source)
        layout.addStretch()

        target_widget = QWidget()
        splitter.addWidget(target_widget)
        layout = QVBoxLayout(target_widget)
        label = QLabel("Target")
        label.setFont(font)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.target = SkeletonDefinitionWidget("target", self)
        layout.addWidget(self.target)
        layout.addStretch()

        scroll.setWidget(splitter)
        scroll.setWidgetResizable(True)

        retarget_button = QPushButton("Attach Skeletons")
        retarget_button.released.connect(self.attach_skeletons)
        vbox.addWidget(retarget_button)

        self.fbx_browser = FBXFileBrowser(self)
        vbox.addWidget(self.fbx_browser)

    def attach_skeletons(self):
        source_joints = self.source.joints()
        target_joints = self.target.joints()
        attach_skeletons(source_joints, target_joints)


class SkeletonDefinitionWidget(QWidget):
    def __init__(self, name, parent=None):
        """Constructor

        :param name: Unique name
        :param parent: Parent QWidget.
        """
        super(SkeletonDefinitionWidget, self).__init__(parent)
        layout = QFormLayout(self)
        for part in Parts():
            setattr(
                self, part, MayaNodeWidget(name="{}.{}".format(name, part), parent=self)
            )
            widget = getattr(self, part)
            label = part.replace("_", " ").title()
            layout.addRow(label, widget)
        layout.setSpacing(0)

    def joints(self):
        return [getattr(self, part).node for part in Parts()]


class FBXFileBrowser(QWidget):
    def __init__(self, parent=None):
        """Constructor

        :param parent: Parent QWidget.
        """
        super(FBXFileBrowser, self).__init__(parent)
        self.create_actions()

        layout = QVBoxLayout(self)
        self.file_model = QFileSystemModel(self)
        self.root_path = FilePathWidget(
            "Root Directory: ",
            FilePathWidget.directory,
            name="cmt.ikrig.fbxfilebrowser.rootpath",
            parent=self,
        )
        self.root_path.path_changed.connect(self.set_root_path)
        layout.addWidget(self.root_path)

        self.file_tree_view = QTreeView()
        self.file_model.setFilter(QDir.NoDotAndDotDot | QDir.Files | QDir.AllDirs)
        self.file_model.setReadOnly(True)
        self.file_model.setNameFilters(["*.fbx"])
        self.file_model.setNameFilterDisables(False)
        self.file_tree_view.setModel(self.file_model)
        self.file_tree_view.setColumnHidden(1, True)
        self.file_tree_view.setColumnHidden(2, True)
        self.file_tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_tree_view.customContextMenuRequested.connect(
            self.on_file_tree_context_menu
        )
        self.file_tree_view.doubleClicked.connect(self.on_file_tree_double_clicked)
        self.file_tree_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.file_tree_view)
        self.set_root_path(self.root_path.path)

    def create_actions(self):
        return
        self.propagate_neutral_action = QAction(
            "Propagate Neutral Update",
            toolTip="Propagate updates to a neutral mesh to the selected targets.",
            triggered=self.propagate_neutral_update,
        )

        self.export_selected_action = QAction(
            "Export Selected Meshes",
            toolTip="Export the selected meshes to the selected directory",
            triggered=self.export_selected,
        )

    def create_menu(self):
        return
        menubar = self.menuBar()
        menu = menubar.addMenu("Shapes")
        menu.addAction(self.propagate_neutral_action)
        menu.addAction(self.export_selected_action)

    def set_root_path(self, path):
        index = self.file_model.setRootPath(path)
        self.file_tree_view.setRootIndex(index)

    def on_file_tree_double_clicked(self, index):
        path = self.file_model.fileInfo(index).absoluteFilePath()
        if not os.path.isfile(path) or not path.lower().endswith(".fbx"):
            return
        import_fbx(path)

    def on_file_tree_context_menu(self, pos):
        index = self.file_tree_view.indexAt(pos)

        if not index.isValid():
            return

        path = self.file_model.fileInfo(index).absoluteFilePath()
        if not os.path.isfile(path) or not path.lower().endswith(".fbx"):
            return

        sel = cmds.ls(sl=True)

        menu = QMenu()
        # menu.addAction(QAction("Import selected", self, triggered=self.import_selected_objs))
        # menu.addAction(QAction("Retarget selected", self, triggered=self.import_selected_objs))
        menu.exec_(self.file_tree_view.mapToGlobal(pos))

    def get_selected_paths(self):
        indices = self.file_tree_view.selectedIndexes()
        if not indices:
            return []
        paths = [
            self.file_model.fileInfo(idx).absoluteFilePath()
            for idx in indices
            if idx.column() == 0
        ]
        return paths

    def import_selected_fbx(self):
        """Import the selected shapes in the tree view.

        If a mesh with a blendshape is selected in the scene, the shapes will be added
        as targets
        """
        indices = self.file_tree_view.selectedIndexes()
        if not indices:
            return None
        paths = self.get_selected_paths()
        # Import fbx

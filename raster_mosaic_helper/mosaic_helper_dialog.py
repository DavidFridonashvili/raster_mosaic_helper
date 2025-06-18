from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import (
    QDialog, QFileDialog, QMessageBox, QCheckBox, QApplication, QSizePolicy
)
from PyQt5.QtCore import Qt
import os
import tempfile
from qgis.core import QgsProject, QgsRasterLayer, QgsApplication
import processing

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'app.ui'))

class MosaicHelperDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # Connect UI buttons
        self.btn_use_loaded_layers.clicked.connect(self.use_loaded_layers_and_open_mosaic)
        self.chk_select_all.stateChanged.connect(self.toggle_select_all)

        # Store checkboxes here
        self.checkboxes = []

        self.populate_raster_checkboxes()
        self.chk_select_all.setChecked(True)

    def showEvent(self, event):
        super().showEvent(event)
        self.populate_raster_checkboxes()

    def populate_raster_checkboxes(self):
        # Clear existing checkboxes from layout
        for i in reversed(range(self.checkBoxLayout.count())):
            self.checkBoxLayout.setStretch(i, 0)
            widget = self.checkBoxLayout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.checkboxes = []

        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsRasterLayer):
                path = layer.dataProvider().dataSourceUri()
                if path.lower().endswith(".tif"):
                    cb = QCheckBox(layer.name())
                    cb.setChecked(True)
                    cb.setProperty("path", path)

                    # Force minimal internal spacing & height
                    cb.setStyleSheet("""
                        QCheckBox {
                            margin-top: 0px;
                            margin-bottom: 0px;
                            padding-top: 0px;
                            padding-bottom: 0px;
                        }
                        QCheckBox::indicator {
                            margin: 0px;
                            padding: 0px;
                            width: 14px;
                            height: 14px;
                        }
                    """)

                    cb.setFixedHeight(18)
                    cb.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

                    self.checkBoxLayout.addWidget(cb)
                    self.checkboxes.append(cb)

        # Ensure layout and scroll area contents have no margins or spacing
        self.checkBoxLayout.setSpacing(0)
        self.checkBoxLayout.setContentsMargins(0, 0, 0, 0)

        if self.scrollAreaWidgetContents.layout() is not None:
            self.scrollAreaWidgetContents.layout().setContentsMargins(0, 0, 0, 0)


    def toggle_select_all(self, state):
        check = state == Qt.Checked
        for cb in self.checkboxes:
            cb.setChecked(check)

    def use_loaded_layers_and_open_mosaic(self):
        paths = []
        for cb in self.checkboxes:
            if cb.isChecked():
                path = cb.property("path")
                paths.append(f'"{path}"')

        if not paths:
            QMessageBox.warning(self, "No rasters", "No .tif raster layers selected.")
            return

        temp_path = os.path.join(tempfile.gettempdir(), "saga_input_list.txt")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write("\n".join(paths))

        clipboard = QApplication.clipboard()
        clipboard.setText(temp_path)

        alg = QgsApplication.processingRegistry().algorithmById("sagang:mosaicking")
        if not alg:
            QMessageBox.critical(self, "Error", "SAGA Mosaicking tool not found.")
            return

        processing.execAlgorithmDialog("sagang:mosaicking", {'INPUT': temp_path})

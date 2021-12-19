# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : Calc Area 2.
Description          : Show layer area and length when editing
Date                 : December, 2021
copyright            : (C) 2021 by Luiz Motta
email                : motta.luiz@gmail.com

 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Luiz Motta'
__date__ = '2021-12-22'
__copyright__ = '(C) 2021, Luiz Motta'
__revision__ = '$Format:%H$'


from qgis.PyQt.QtCore import pyqtSlot
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QComboBox,
    QLabel,
    QDialogButtonBox,
    QSpacerItem, QSizePolicy
)

from qgis.core import QgsUnitTypes
from qgis.gui import QgsMessageBar, QgsProjectionSelectionWidget


def boldLabel(lbl):
    font = lbl.font()
    font.setBold( True )
    lbl.setFont( font )

def buttonOkCancel():
    def changeDefault(standardButton, default):
        btn = btnBox.button( standardButton )
        btn.setAutoDefault( default )
        btn.setDefault( default )

    btnBox = QDialogButtonBox( QDialogButtonBox.Ok | QDialogButtonBox.Cancel )
    changeDefault( QDialogButtonBox.Ok, False )
    changeDefault( QDialogButtonBox.Cancel, True )
    return btnBox


class DialogSetup(QDialog):
    def __init__(self, parent, title, crs, unitLength, unitArea):
        super().__init__( parent )
        self.title = title
        self.msgBar = QgsMessageBar()

        lytCrs = self._layoutCrs( crs ) # self.psCrs
        lytUnitLength = self._layoutUnitLength( unitLength ) # self.cmbUnitLength
        lytUnitArea = self._layoutUnitArea( unitArea ) # self.cmbUnitArea

        self.setWindowTitle( title )
        lytMain = QVBoxLayout()
        lytMain.addWidget( self.msgBar )
        for lyt in ( lytCrs, lytUnitLength, lytUnitArea ):
            lytMain.addLayout( lyt )

        btnBox = buttonOkCancel()
        btnBox.accepted.connect( self.accept )
        btnBox.rejected.connect( self.reject )
        lytMain.addWidget( btnBox )
        lytMain.addItem( QSpacerItem( 10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding ) )
        self.setLayout( lytMain )

    def currentData(self):
        return {
            'crs': self.psCrs.crs(),
            'unitLength': self.cmbUnitLength.currentData(),
            'unitArea': self.cmbUnitArea.currentData()
        }

    def _layoutCrs(self, crs):
        def projectionSelectionWidget():
            p = QgsProjectionSelectionWidget()
            for opt in ( p.LayerCrs, p.ProjectCrs, p.CurrentCrs, p.DefaultCrs, p.RecentCrs ):
                p.setOptionVisible( opt, False )
            return p

        @pyqtSlot('QgsCoordinateReferenceSystem')
        def crsChanged(crs):
            if crs.isGeographic():
                self._messageErrorCrs()

        self.psCrs = projectionSelectionWidget()
        self.psCrs.setCrs( crs )
        self.psCrs.crsChanged.connect( crsChanged )

        lyt = QVBoxLayout()
        label = QLabel( self.tr('Coordinate Reference System') )
        boldLabel( label )
        lyt.addWidget( label )
        lyt.addWidget( self.psCrs )

        return lyt

    def _layoutUnit(self, title, units, current):
        cmb = QComboBox()
        for item in units:
            cmb.addItem( QgsUnitTypes.toString( item ), item )
        cmb.setCurrentText( QgsUnitTypes.toString( current ) )

        lyt = QHBoxLayout()
        label = QLabel( title )
        boldLabel( label )
        lyt.addWidget( label )
        lyt.addWidget( cmb )

        return cmb, lyt

    def _layoutUnitLength(self, unit):
        units = [
            QgsUnitTypes.DistanceMeters,
            QgsUnitTypes.DistanceKilometers,
            QgsUnitTypes.DistanceFeet,
            QgsUnitTypes.DistanceYards,
            QgsUnitTypes.DistanceMiles
        ]
        title = self.tr('Length unit')
        cmb, lyt = self._layoutUnit( title, units, unit )

        self.cmbUnitLength = cmb
        return lyt

    def _layoutUnitArea(self, unit):
        units = [
            QgsUnitTypes.AreaSquareMeters,
            QgsUnitTypes.AreaSquareKilometers,
            QgsUnitTypes.AreaSquareFeet,
            QgsUnitTypes.AreaSquareYards,
            QgsUnitTypes.AreaSquareMiles,
            QgsUnitTypes.AreaHectares,
            QgsUnitTypes.AreaAcres
        ]
        title = self.tr('Area unit')
        cmb, lyt = self._layoutUnit( title, units, unit )

        self.cmbUnitArea = cmb
        return lyt

    def _messageErrorCrs(self):
        msg = self.tr('Invalid CRS(need be projected)')
        self.msgBar.pushCritical( self.title, msg )

    @pyqtSlot()
    def accept(self):
        crs = self.psCrs.crs()
        if not crs.isValid() or crs.isGeographic():
            self._messageErrorCrs()
            return

        super().accept()

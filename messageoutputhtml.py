"""
/***************************************************************************
Name                 : Message Output Html
Description          : Function for show "locale".html in QgsMessageOutput
Date                 : August, 2021
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
__date__ = '2021-08-01'
__copyright__ = '(C) 2021, Luiz Motta'
__revision__ = '$Format:%H$'

import os

from qgis.core import QgsApplication, QgsMessageOutput



def messageOutputHtml(title, prefixHtml, dirHtml):
    def readFile(filepath):
        with open(filepath, 'r') as reader:
            content = reader.read()
        return content

    dlg = QgsMessageOutput.createMessageOutput()
    dlg.setTitle( title )

    pathCurrent = os.getcwd()
    os.chdir( dirHtml )
    file = f"{prefixHtml}_{QgsApplication.locale()}.html"
    if not os.path.exists( file):
        file = f"{prefixHtml}_en.html"
    content = readFile( file )
    dlg.setMessage( content, QgsMessageOutput.MessageHtml )
    dlg.showMessage()
    os.chdir( pathCurrent )

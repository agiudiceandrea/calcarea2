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

def classFactory(iface):
    from .plugin import CalcAreaPlugin
    return CalcAreaPlugin( iface )

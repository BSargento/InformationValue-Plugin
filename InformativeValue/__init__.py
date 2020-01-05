# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ValorInformativo
                                 A QGIS plugin
 Calcula o Valor Informativo
                             -------------------
        begin                : 2017-12-21
        copyright            : (C) 2017 by BSargento
        email                : bernardosargento@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load ValorInformativo class from file ValorInformativo.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .ValorInformativo import ValorInformativo
    return ValorInformativo(iface)

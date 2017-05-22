# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2017 Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Show Contact Type',
    'version': '0.1',
    'summary': '',
    'category': 'Hidden',
    'description': """Show the contact type in the partner name on sale orders and other documents.
Which types that should show in the name can be configured through the parameter partner_show_contact_type.types. It's a space separated list of partner type values (i.e. 'invoice delivery').""",
    'author': 'Vertel AB',
    'website': 'http://www.vertel.se',
    'depends': ['sale'],
    'data': [
    ],
    'installable': True,
}

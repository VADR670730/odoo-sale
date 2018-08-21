# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2016 Vertel AB (<http://vertel.se>).
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

from openerp import api, models, fields, _
from openerp import tools
from openerp.osv import orm
from openerp.osv import fields as old_fields
import base64

import logging
_logger = logging.getLogger(__name__)

class ir_attachment(models.Model):
    _inherit = "ir.attachment"

    sequence = fields.Integer()

class ProductTemplate(models.Model):
    _inherit = "product.template"

    # We must stick to one stored computed field here. Having multiple brings out a swarm of bugs in the framework.
    image_main_id = fields.Many2one(comodel_name='ir.attachment',string="Main image",compute='_get_image_main_id',store=True)
    image_main_medium_id = fields.Many2one(comodel_name='ir.attachment',string="Medium image")
    image_main_small_id = fields.Many2one(comodel_name='ir.attachment',string="Small image")

    image_attachment_ids = fields.Many2many(string='Images', comodel_name='ir.attachment')
    image_main = fields.Binary(compute='_get_multi_image')
    image_main_medium = fields.Binary(compute='_get_multi_image')
    image_main_small = fields.Binary(compute='_get_multi_image')

    @api.one
    @api.depends('image_attachment_ids', 'image_attachment_ids.sequence', 'image_attachment_ids.datas', 'product_variant_ids.image_attachment_ids', 'product_variant_ids.image_attachment_ids.sequence', 'product_variant_ids.image_attachment_ids.datas')
    def _get_image_main_id(self):
        # Changes to anything other than image_main_id must be done with a write
        _logger.warn('%s._get_image_main_id: %s context: %s' % (self, self.image_attachment_ids, self._context))
        # A lack of variants indicate that we're in a create. The writes below will trigger an error deep in the framework.
        # I mean waaayy up inside there. We do not want to deal with that ss... stuff. This skirts around the problem.
        if not self.product_variant_ids:
            return
        # Update variants first
        self.product_variant_ids._get_v_image_main_id()
        if self.image_attachment_ids:
            self.image_main_id = self.image_attachment_ids.sorted(lambda r: r.sequence)[0]
        else:
            images = self.product_variant_ids.filtered(lambda v: v.default_variant == True).mapped('image_attachment_ids').sorted(lambda r: r.sequence)
            if not images:
                images = self.product_variant_ids.mapped('image_attachment_ids').sorted(lambda r: r.sequence)
            self.image_main_id = images and images[0]
        image = self.image_main_id.with_context(bin_size=False).datas
        try:
            images = tools.image_get_resized_images(image)
            images = {
                'image_main': image,
                'image_main_medium': images['image_medium'],
                'image_main_small': images['image_small'],
            }
        except:
            images = {
                'image_main': image,
                'image_main_medium': False,
                'image_main_small': False,
            }
        if not self.image_main_medium_id:
            self.write({'image_main_medium_id': self.env['ir.attachment'].create({
                        'name': 'autogenerated_%s_medium' % self.name,
                        'res_name': self.name,
                        'res_model': self._name,
                        'datas': images['image_main_medium'],
                        'datas_fname': '%s_medium' % self.name ,
                    }).id})
        else:
            self.image_main_medium_id.write({'datas': images['image_main_medium']})
        if not self.image_main_small_id:
            self.write({'image_main_small_id': self.env['ir.attachment'].create({
                        'name': 'autogenerated_%s_small' % self.name,
                        'res_name': self.name,
                        'res_model': self._name,
                        'datas': images['image_main_small'],
                        'datas_fname': '%s_small' % self.name ,
                    }).id})
        else:
            self.image_main_small_id.write({'datas': images['image_main_small']})

    @api.multi
    def _get_multi_image(self):
        """Get the main image for this object.
        """
        self.env.cr.execute('SELECT id, image_main_id, image_main_medium_id, image_main_small_id FROM %s WHERE id IN %%s;' % self._table, [self._ids])
        res = self.env.cr.dictfetchall()
        att_ids = set()
        for d in res:
            for f in ['image_main_id', 'image_main_medium_id', 'image_main_small_id']:
                att_ids.add(d[f])
        attachments = self.env['ir.attachment'].with_context(bin_size=False).search_read([('id', 'in', list(att_ids))], ['datas'])
        for product in self:
            p = filter(lambda x: x.get('id') == product.id, res)
            product.image_main = p[0]['image_main_id'] and (filter(lambda x: x.get('id') == p[0]['image_main_id'], attachments) or [{}])[0].get('datas')
            product.image_main_medium = p[0]['image_main_medium_id'] and (filter(lambda x: x.get('id') == p[0]['image_main_medium_id'], attachments) or [{}])[0].get('datas')
            product.image_main_small = p[0]['image_main_small_id'] and (filter(lambda x: x.get('id') == p[0]['image_main_small_id'], attachments) or [{}])[0].get('datas')

    @api.multi
    def get_image_attachment_ids(self):
        self.ensure_one()
        res = self.sudo().image_attachment_ids.sorted(lambda r: r.sequence).mapped('id')
        return res + [id for id in self.env['product.product'].search([('id', '=', self.id)]).sudo().sorted(lambda r: r.sequence).mapped('id') if id not in res]

    @api.model
    def update_image_attachments(self):
        limit = int(self.env['ir.config_parameter'].get_param('product_multi_image_attachment.template_limit', '50'))
        offset = int(self.env['ir.config_parameter'].get_param('product_multi_image_attachment.template_offset', '0'))
        products = self.with_context(active_test=False).search([], limit=limit, offset=offset)
        products and products._get_image_main_id()
        self.env['ir.config_parameter'].set_param('product_multi_image_attachment.template_offset', str(offset + limit))

class ProductTemplateOld(orm.Model):
    """Reference core image old_fields to multi-image variants.

    It is needed to use v7 api here because core model old_fields use the ``multi``
    attribute, that has no equivalent in v8, and it needs to be disabled or
    bad things will happen. For more reference, see
    https://github.com/odoo/odoo/issues/10799
    """
    _inherit = "product.template"
    _columns = {
        "image": old_fields.related(
            "image_main",
            type="binary",
            store=False,
            multi=False),
        "image_medium": old_fields.related(
            "image_main_medium",
            type="binary",
            store=False,
            multi=False),
        "image_small": old_fields.related(
            "image_main_small",
            type="binary",
            store=False,
            multi=False)
    }

class ProductProduct(models.Model):
    _inherit = "product.product"

    image_main_id = fields.Many2one(comodel_name='ir.attachment', string="Main image")
    image_main_medium_id = fields.Many2one(comodel_name='ir.attachment', string="Medium image")
    image_main_small_id = fields.Many2one(comodel_name='ir.attachment', string="Small image")
    image_attachment_ids = fields.Many2many(string='Images', comodel_name='ir.attachment')
    image_main = fields.Binary(compute='_get_v_multi_image')
    image_main_medium = fields.Binary(compute='_get_v_multi_image')
    image_main_small = fields.Binary(compute='_get_v_multi_image')

    @api.one
    def _get_v_image_main_id(self):
        # All changes in this function must be done with a write
        _logger.warn('%s._get_v_image_main_id: %s context: %s' % (self, self.image_attachment_ids, self._context))
        
        if self.image_attachment_ids:
            self.write({'image_main_id': self.image_attachment_ids.sorted(lambda r: r.sequence)[0].id})
        elif self.product_tmpl_id.image_attachment_ids:
            self.write({'image_main_id': self.product_tmpl_id.image_attachment_ids.sorted(lambda r: r.sequence)[0].id})
        else:
            self.write({'image_main_id': False})
        image = self.image_main_id.with_context(bin_size=False).datas
        try:
            images = tools.image_get_resized_images(image)
            images = {
                'image_main': image,
                'image_main_medium': images['image_medium'],
                'image_main_small': images['image_small'],
            }
        except:
            images = {
                'image_main': image,
                'image_main_medium': False,
                'image_main_small': False,
            }
        if not self.image_main_medium_id:
            self.write({'image_main_medium_id': self.env['ir.attachment'].create({
                        'name': 'autogenerated_%s_medium' % self.name,
                        'res_name': self.name,
                        'res_model': self._name,
                        # ~ 'res_id': self.id,
                        'datas': images['image_main_medium'],
                        'datas_fname': '%s_medium' % self.name ,
                    }).id})
        else:
            self.image_main_medium_id.write({'datas': images['image_main_medium']})
        if not self.image_main_small_id:
            self.write({'image_main_small_id': self.env['ir.attachment'].create({
                        'name': 'autogenerated_%s_small' % self.name,
                        'res_name': self.name,
                        'res_model': self._name,
                        # ~ 'res_id': self.id,
                        'datas': images['image_main_small'],
                        'datas_fname': '%s_small' % self.name ,
                    }).id})
        else:
            self.image_main_small_id.write({'datas': images['image_main_small']})

    @api.multi
    def get_image_attachment_ids(self):
        self.ensure_one()
        res = self.sudo().image_attachment_ids.sorted(lambda r: r.sequence).mapped('id')
        return  res + [id for id in self.sudo().product_tmpl_id.image_attachment_ids.sorted(lambda r: r.sequence).mapped('id') if id not in res]

    @api.multi
    def _get_v_multi_image(self):
        """Get the main image for this object.
        """
        _logger.warn('%s._get_v_multi_image()' % self)
        self.env.cr.execute('SELECT id, image_main_id, image_main_medium_id, image_main_small_id FROM %s WHERE id IN %%s;' % self._table, [self._ids])
        res = self.env.cr.dictfetchall()
        att_ids = set()
        for d in res:
            for f in ['image_main_id', 'image_main_medium_id', 'image_main_small_id']:
                att_ids.add(d[f])
        attachments = self.env['ir.attachment'].with_context(bin_size=False).search_read([('id', 'in', list(att_ids))], ['datas'])
        for product in self:
            p = filter(lambda x: x.get('id') == product.id, res)
            product.image_main = p[0]['image_main_id'] and (filter(lambda x: x.get('id') == p[0]['image_main_id'], attachments) or [{}])[0].get('datas')
            product.image_main_medium = p[0]['image_main_medium_id'] and (filter(lambda x: x.get('id') == p[0]['image_main_medium_id'], attachments) or [{}])[0].get('datas')
            product.image_main_small = p[0]['image_main_small_id'] and (filter(lambda x: x.get('id') == p[0]['image_main_small_id'], attachments) or [{}])[0].get('datas')

    @api.model
    def update_image_attachments(self):
        limit = int(self.env['ir.config_parameter'].get_param('product_multi_image_attachment.product_limit', '50'))
        offset = int(self.env['ir.config_parameter'].get_param('product_multi_image_attachment.product_offset', '0'))
        products = self.with_context(active_test=False).search([], limit=limit, offset=offset)
        products and products._get_v_image_main_id()
        self.env['ir.config_parameter'].set_param('product_multi_image_attachment.product_offset', str(offset + limit))

class ProductProductOld(orm.Model):
    """It is needed to use v7 api here because core model fields use the
    ``multi`` attribute, that has no equivalent in v8, and it needs to be
    disabled or bad things will happen. For more reference, see
    https://github.com/odoo/odoo/issues/10799

    Needed for getting the correct data in the inheritance chain. Probably
    in v10 this won't be needed as the inheritance has been globally
    redesigned.
    """

    _inherit = "product.product"
    _columns = {
        "image": old_fields.related(
            "image_main", type="binary", store=False, multi=False),
        "image_medium": old_fields.related(
            "image_main_medium", type="binary", store=False, multi=False),
        "image_small": old_fields.related(
            "image_main_small", type="binary", store=False, multi=False)
    }

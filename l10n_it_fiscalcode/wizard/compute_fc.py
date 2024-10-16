# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

_logger = logging.getLogger(__name__)

try:
    from codicefiscale import build

except ImportError:
    _logger.warning(
        "codicefiscale library not found. "
        "If you plan to use it, please install the codicefiscale library"
        " from https://pypi.python.org/pypi/codicefiscale"
    )


class WizardComputeFc(models.TransientModel):
    _name = "wizard.compute.fc"
    _description = "Compute Fiscal Code"
    _rec_name = "fiscalcode_surname"

    fiscalcode_surname = fields.Char("Surname", required=True, size=64)
    fiscalcode_firstname = fields.Char("First name", required=True, size=64)
    birth_date = fields.Date("Date of birth", required=True)
    birth_city = fields.Many2one(
        "res.city.it.code.distinct", required=True, string="City of birth"
    )
    birth_province = fields.Many2one(
        "res.country.state", required=True, string="Province"
    )
    sex = fields.Selection([("M", "Male"), ("F", "Female")], required=True)

    @api.onchange("birth_city")
    def onchange_birth_city(self):
        self.ensure_one()

        it = self.env.ref("base.it").id
        res = {
            "domain": {"birth_province": [("country_id", "=", it)]},
            "value": {"birth_province": False},
        }

        if self.birth_city:
            # SMELLS: Add a foreign key in "res_city_it_code"
            #          instead using the weak link "code" <-> "province".
            #
            city_ids = self.env["res.city.it.code"].search(
                [("name", "=", self.birth_city.name)]
            )
            provinces = city_ids.mapped("province")
            province_ids = self.env["res.country.state"].search(
                [("country_id", "=", it), ("code", "in", provinces)]
            )

            res["domain"]["birth_province"] = expression.AND(
                [res["domain"]["birth_province"], [("id", "in", province_ids.ids)]]
            )

            if len(province_ids) == 1:
                res["value"]["birth_province"] = province_ids.id

        return res

    @api.onchange("birth_province")
    def onchange_birth_province(self):
        self.ensure_one()

        res = {"domain": {"birth_city": []}}

        if not self.birth_city:
            if self.birth_province:
                # SMELLS: Add a foreign key in "res_city_it_code"
                #          instead using the weak link "code" <-> "province".
                #
                city_ids = self.env["res.city.it.code"].search(
                    [("province", "=", self.birth_province.code)]
                )
                names = city_ids.mapped("name")
                distinct_city_ids = self.env["res.city.it.code.distinct"].search(
                    [("name", "in", names)]
                )

                res["domain"]["birth_city"] = expression.AND(
                    [res["domain"]["birth_city"], [("id", "in", distinct_city_ids.ids)]]
                )

        return res

    def _get_national_code(self, birth_city, birth_prov, birth_date):
        """
        notes fields contains variation data while var_date may contain the
        eventual date of the variation. notes may be:
        - ORA: city changed name, name_var contains new name, national_code_var
               contains the repeated national code.
               There are some cities that contains two identical values, for
               example PORTO (CO), has two ORA entries for G906 and G907, this
               is rather unpredictable and the first value will be taken
        - AGG: city has been aggregated to another one and doesn't exist
               anymore. name_var and national_code_var contain recent data.
               Some cities have particular cases, for example ALME' (BG) that
               is listed as aggregate to another city since 1927 but gained
               independence (creation_date) in 1948
        - AGP: partially aggregated, city has been split and assigned to more
               than one other cities. name_var and national_code_var contain
               recent data. It's not possible to determine the correct code
               for new city so the original code is returned
        - AGT: temporarily aggregated to another city, if possible this gets
               ignored. name_var and national_code_var contain recent data
        - VED: reference to another city. This is assigned to cities that
               changed name and were then subject to other changes.
        """
        cities = self.env["res.city.it.code"].search(
            [("name", "=", birth_city), ("province", "=", birth_prov)],
            order="creation_date ASC, var_date ASC, notes ASC",
        )
        if not cities or len(cities) == 0:
            return ""
        # Checks for any VED element
        newcts = None
        for ct in cities:
            if ct.notes == "VED":
                newcts = self.env["res.city.it.code"].search(
                    [("name", "=", ct.name_var)]
                )
                break
        if newcts:
            cities = newcts
        return self._check_national_codes(birth_date, cities)

    def _check_national_codes(self, birth_date, cities):
        nc = ""
        dtcostvar = None
        for ct in cities:
            if ct.creation_date and (
                not dtcostvar or not ct.creation_date or dtcostvar < ct.creation_date
            ):
                dtcostvar = ct.creation_date
            if not ct.notes:
                nc = ct.national_code
            elif ct.notes == "ORA" and (
                not dtcostvar or not ct.var_date or dtcostvar < ct.var_date
            ):
                if not ct.var_date or ct.var_date <= birth_date:
                    nc = ct.national_code_var
                elif not nc:
                    nc = ct.national_code
                if ct.var_date:
                    dtcostvar = ct.var_date
            elif ct.notes == "AGG" and (
                not dtcostvar or not ct.var_date or dtcostvar < ct.var_date
            ):
                if not ct.var_date or ct.var_date <= birth_date:
                    nc = ct.national_code_var
                elif not nc:
                    nc = ct.national_code
                if ct.var_date:
                    dtcostvar = ct.var_date
            elif ct.notes == "AGP" and (
                not dtcostvar or not ct.var_date or dtcostvar < ct.var_date
            ):
                nc = ct.national_code
                if ct.var_date:
                    dtcostvar = ct.var_date
            elif ct.notes == "AGP" and (
                not dtcostvar or not ct.var_date or dtcostvar < ct.var_date
            ):
                nc = ct.national_code

        return nc

    def compute_fc(self):
        active_id = self._context.get("active_id")
        partner = self.env["res.partner"].browse(active_id)
        for f in self:
            if (
                not f.fiscalcode_surname
                or not f.fiscalcode_firstname
                or not f.birth_date
                or not f.birth_city
                or not f.sex
            ):
                raise UserError(_("One or more fields are missing"))
            nat_code = self._get_national_code(
                f.birth_city.name, f.birth_province.code, f.birth_date
            )
            if not nat_code:
                raise UserError(_("National code is missing"))
            c_f = build(
                f.fiscalcode_surname,
                f.fiscalcode_firstname,
                f.birth_date,
                f.sex,
                nat_code,
            )
            if partner.fiscalcode and partner.fiscalcode != c_f:
                raise UserError(
                    _(
                        "Existing fiscal code %(partner_fiscalcode)s is different "
                        "from the computed one (%(compute)s). If you want to use"
                        " the computed one, remove the existing one"
                    )
                    % {"partner_fiscalcode": partner.fiscalcode, "compute": c_f}
                )
            partner.fiscalcode = c_f
            partner.company_type = "person"
        return {"type": "ir.actions.act_window_close"}

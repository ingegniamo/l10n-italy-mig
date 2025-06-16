from odoo import fields, models
from odoo.tools import SQL


class AccountGroup(models.Model):
    _inherit = "account.group"
    account_balance_sign = fields.Integer(
        compute="_compute_account_balance_sign",
        string="Balance sign",
    )
    current_account_ids = fields.One2many(
        "account.account", compute="_compute_current_account_ids"
    )

    def _compute_current_account_ids(self):
        """Retrieves every account from `self` and `self`'s subgroups.
        In Odoo 18 the group_id on account is not stored so it raises
        an error the one2many account_ids with inverse name group_id."""
        group_ids = self.ids
        self.current_account_ids = self.env["account.account"]
        if not group_ids:
            return
        group_ids = SQL(",".join(map(str, group_ids)))
        results = self.env.execute_query(
            SQL(
                """
SELECT
 agroup.id AS group_id,
STRING_AGG(DISTINCT account.id::text, ', ') as account_ids
FROM  account_group agroup
left join account_account account
ON agroup.code_prefix_start <= LEFT(%(code_store)s->>%(root_company_id)s,
char_length(agroup.code_prefix_start))
AND agroup.code_prefix_end >= LEFT(%(code_store)s->>%(root_company_id)s,
char_length(agroup.code_prefix_end))
AND agroup.company_id = %(root_company_id)s
AND agroup.id IN (%(group_ids)s)
GROUP BY group_id
            """,
                code_store=SQL.identifier("account", "code_store"),
                group_ids=group_ids,
                root_company_id=str(self.env.company.root_id.id),
            )
        )
        group_by_code = dict(results)
        self.current_account_ids = self.env["account.account"]
        if not group_by_code:
            return
        for record in self:
            record.current_account_ids = list(
                map(int, group_by_code.get(record.id, "").split(", "))
            )

    def _compute_account_balance_sign(self):
        for group in self:
            group.account_balance_sign = group.get_account_balance_sign()

    def get_account_balance_sign(self):
        self.ensure_one()
        progenitor = self.get_group_progenitor()
        accounts = progenitor.get_group_accounts()
        if accounts:
            return accounts[0].account_balance_sign
        return 1

    def get_group_accounts(self):
        """Retrieves every account from `self` and `self`'s subgroups."""
        return (self + self.get_group_subgroups()).mapped("current_account_ids")

    def get_group_progenitor(self):
        self.ensure_one()
        if not self.parent_id:
            return self
        return self.get_group_parents().filtered(lambda g: not g.parent_id)

    def get_group_parents(self):
        """
        Retrieves every parent for group `self`.
        :return: group's parents as recordset, or empty recordset if `self`
        has no parents. If a recursion is found, an error is raised.
        """
        self.ensure_one()
        parent_ids = []
        parent = self.parent_id
        while parent:
            parent_ids.append(parent.id)
            parent = parent.parent_id
        return self.browse(parent_ids)

    def get_group_subgroups(self):
        """Retrieves every subgroup for groups `self`."""
        subgroups_ids = self.search([("id", "child_of", self.ids)])
        return subgroups_ids

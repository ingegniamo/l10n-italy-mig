# Migration stub for Odoo 17 -> 19: this module intentionally ships no code.
# Its only purpose is to provide a 19.0 manifest WITHOUT the
# `excludes: ['l10n_it_edi']` declaration, so that update_list clears the stale
# exclusion record inherited from the OCA 17 version and the native
# `l10n_it_edi` localization can be installed. To be uninstalled once the
# fatturapa data has been migrated to the native fields (see migration_account_18).

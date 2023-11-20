/** @odoo-module **/
import { actionService } from "@web/webclient/actions/action_service";
import { patch } from "@web/core/utils/patch";

patch(actionService,{
            /**
             * @override
             */
            _executeReportClientAction: function (action, options) {
                const MODULE_NAME = "l10n_it_financial_statements_report";

                // Same hack as account_financial_report to apply its report controller.
                if (action.report_name.startsWith(`${MODULE_NAME}.`)) {
                    const urls = this._makeReportUrls(action);
                    const clientActionOptions = _.extend({}, options, {
                        context: action.context,
                        data: action.data,
                        display_name: action.display_name,
                        name: action.name,
                        report_file: action.report_file,
                        report_name: action.report_name,
                        report_url: urls.html,
                    });
                    return this.doAction(
                        "account_financial_report.client_action",
                        clientActionOptions
                    );
                }
                return this._super.apply(this, arguments);
            },
        });
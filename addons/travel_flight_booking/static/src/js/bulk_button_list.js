odoo.define('travel_flight_booking.bulk_button_list', function (require) {
    'use strict';

    var ListController = require('web.ListController');

    ListController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            try {
                if (this.modelName === 'flight.booking' && this.renderer && this.renderer.viewType === 'list') {
                    var self = this;
                    var $buttons = this.$buttons || $node.find('.o_control_panel .o_cp_buttons');
                    if ($buttons && $buttons.find('.o_button_bulk_upload').length === 0) {
                        var $btn = $('<button type="button" class="btn btn-secondary o_button_bulk_upload">Bulk Upload</button>');
                        $btn.on('click', function () {
                            self.do_action('travel_flight_booking.action_flight_booking_bulk_upload');
                        });
                        $buttons.append($btn);
                        this.$buttons = $buttons;
                    }
                }
            } catch (e) {
                console.error('bulk_button_list error', e);
            }
        },
    });
});

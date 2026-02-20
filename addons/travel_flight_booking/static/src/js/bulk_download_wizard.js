odoo.define('travel_flight_booking.bulk_download_wizard', function (require) {
    'use strict';

    var FormController = require('web.FormController');
    var rpc = require('web.rpc');
    var core = require('web.core');

    // Delegated click handler so footer buttons rendered later are caught
    $(document).on('click', '.o_bulk_download_sample', function (ev) {
        ev.preventDefault();
        try {
            var url = new URL('/travel_flight_booking/sample_download', window.location.origin);
            url.searchParams.set('format', 'xlsx');
            // open in new tab/window so browser handles session cookie and download
            window.open(url.toString(), '_blank');
        } catch (e) {
            console.error('bulk download open error', e);
        }
    });
});

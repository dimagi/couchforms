
function parse_date(date_string) {
    if (!date_string) return new Date(0); // 1970-01-01T00:00:00Z
    // hat tip: http://stackoverflow.com/questions/2587345/javascript-date-parse    

    // We store all dates as ISO-8601, so the timezone is embedded in the string
    // and modern JS implementations understand this.
    //
    // Some of our older dates are in yyyy-mm-dd format and modern JS implementations
    // assume this is in UTC time zone, which is also what we want.

    return new Date(date_string)
}
 
function get_date(xform_doc) {
    function get_date_string(xform_doc) {
        // check some expected places for a date
        var meta = xform_doc.form.meta;
        if (meta && meta.timeEnd) return meta.timeEnd;
        if (meta && meta.timeStart) return meta.timeStart;
        if (xform_doc.form.encounter_date) return xform_doc.form.encounter_date;
        return null;
    }
    return parse_date(get_date_string(xform_doc));
}


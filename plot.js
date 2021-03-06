// An object containing all the "global" variables.
var g;

// Load the Visualization API and the piechart package.
google.load('visualization', '1', {'packages':['corechart']});

// Set a callback to run when the Google Visualization API is loaded.
google.setOnLoadCallback(googleAPILoaded);


function slow_consumer_startup(p)
{
    return (p.Sc + p.Wc > (p.L - p.Kp) * p.Wp);
}

function slow_producer_startup(p)
{
    return (p.Sp + p.Wp > (p.L - p.Kc) * p.Wc);
}

function T_GP(p)
{
    if (p.Wp > p.Wc) {
        return p.Wp;
    }

    return p.Wc;
}

function T_SS_best(p)
{
    return (p.Np + p.Nc + (p.Wp + p.Wc) * (p.L - 1)) / p.L;
}

function T_SS(p)
{
    return (p.Kp * p.Wp + p.Kc * p.Wc + p.Np + p.Nc + p.Sp + p.Sc) / p.L;
}

function T_GX(p)
{
    var slow_cons_startup = slow_consumer_startup(p);
    var slow_prod_startup = slow_producer_startup(p);

    if (slow_cons_startup && slow_prod_startup) {
        // Slow consumer and producer startup --> Short queue regime (SS)
        return T_SS(p);
    }

    if (p.Wp == p.Wc) {
        // Perfect lockstep
        return p.Wc;
    }

    if (p.Wc < p.Wp) {
        // Fast consumer

        if (slow_cons_startup) {
            // Slow consumer startup --> Short queue regime (SC)
            m = Math.floor(((p.L - p.Kc) * p.Wc - (p.Sp + p.Wp))/(p.Wp - p.Wc)) + 1;

            return (p.Sc + p.Wc * p.Kc + p.Nc +
                    p.Sp + (m + p.Kp) * p.Wp + p.Np) / (p.L + m);
        }

        // No short queue effects (G1)
        m = Math.floor((p.Sc + (p.Kp - 1) * p.Wc)/(p.Wp - p.Wc)) + p.Kp;

        return p.Wp + p.Np / m;
    }

    // Fast producer

    if (slow_prod_startup) {
        // Slow producer startup --> Short queue regime (SP)
        m = Math.floor(((p.L - p.Kp) * p.Wp - (p.Sc + p.Wc))/(p.Wc - p.Wp)) + 1;

        return (p.Sp + p.Wp * p.Kp + p.Np +
                p.Sc + (m + p.Kc) * p.Wc + p.Nc) / (p.L + m);
    }

    // No short queue effects (G2)
    m = Math.floor((p.Sp + (p.Kc - 1) * p.Wp)/(p.Wc - p.Wp)) + p.Kc;

    return p.Wc + p.Nc / m;
}

function L_crit_SC(p)
{
    if (p.Wp == 0) {
        // Extend the curve when Wp == 0
        p.Wp = 1;
    }

    return 1 + p.Kp + Math.floor((p.Sc + p.Wc) / p.Wp);
}

function L_crit_SP(p)
{
    if (p.Wc == 0) {
        // Extend the curve when Wp == 0
        p.Wc = 1;
    }

    return 1 + p.Kc + Math.floor((p.Sp + p.Wp) / p.Wc);
}

function L_crit(p)
{
    if (p.Wc < p.Wp) {
        return L_crit_SC(p);
    }

    return L_crit_SP(p);
}

function L_crit_SS(p)
{
    var lc_sc = L_crit_SC(p);
    var lc_sp = L_crit_SP(p);

    if (lc_sc < lc_sp) {
        return lc_sc;
    }

    return lc_sp;
}

function get_regime(p)
{
    var scs = slow_consumer_startup(p);
    var sps = slow_producer_startup(p);

    if (scs && sps) {
        return "(SS) Slow producer and consumer startup";
    }

    if (p.Wc < p.Wp) {
        // Fast consumer
        if (scs) {
            // Short queue
            return "(SC) Slow consumer startup";
        }

        // Large queue
        return "(G1) Fast consumer";
    }

    // Fast producer
    if (sps) {
        // Short queue
        return "(SP) Slow producer startup";
    }

    return "(G2) Fast producer";
}

function get_int_val(pname)
{
    return parseInt(document.getElementById(pname).value);
}

// Global prototype.
function Global()
{
    // Grab the 'canvas' element.
    this.chart1div = document.getElementById('curve_chart1');
    this.chart1 = new google.visualization.LineChart(this.chart1div);
    this.options1 = {
      title: 'Average time between two messages',
      curveType: 'none',
      legend: { position: 'top' },
      hAxis: { title: 'Wp' },
      vAxis: { title: 'Clock cycles'}
    };
    google.visualization.events.addListener(this.chart1, 'onmouseover',
                                            mouseoverHandler);

    this.chart2div = document.getElementById('curve_chart2');
    this.chart2 = new google.visualization.LineChart(this.chart2div);
    this.options2 = {
      title: 'Critical queue lengths for SC, SP and SS regimes (when L is below the critical line, the system is in SS, SC or SC regimes)',
      curveType: 'none',
      legend: { position: 'top' },
      hAxis: { title: 'Wp' },
      vAxis : { logScale: true, title: 'Queue length' }
    };


    this.params = {};
    this.update = update;
    this.update();

    function update() {
        var range_mult = 4;
        var new_params = {};

        new_params.Wp = get_int_val('Wp');
        new_params.Wc = get_int_val('Wc');
        new_params.Sp = get_int_val('Sp');
        new_params.Sc = get_int_val('Sc');
        new_params.Np = get_int_val('Np');
        new_params.Nc = get_int_val('Nc');
        new_params.Kp = get_int_val('Kp');
        new_params.Kc = get_int_val('Kc');
        new_params.L = get_int_val('L');

        if (new_params.Wp == this.params.Wp &&
                new_params.Wc == this.params.Wc &&
                new_params.Sp == this.params.Sp &&
                new_params.Sc == this.params.Sc &&
                new_params.Np == this.params.Np &&
                new_params.Nc == this.params.Nc &&
                new_params.Kp == this.params.Kp &&
                new_params.Kc == this.params.Kc &&
                new_params.L == this.params.L) {
            return;
        }
        this.params = new_params;

        var save_Wp = this.params.Wp;
        var data_array;

        // First plot
        data_array = [['W_P', 'T_GP', 'T_SS_best', 'T_Gx']];
        for (var i=1; i<range_mult * this.params.Wc; i++) {
            this.params.Wp = i-1;
            data_array[i] = [
                this.params.Wp,
                T_GP(this.params),
                T_SS_best(this.params),
                T_GX(this.params)
            ];
        }
        var data = google.visualization.arrayToDataTable(data_array);
        this.chart1.draw(data, this.options1);

        // Second plot
        data_array = [['W_P', 'L_crit_SS', 'L_crit']];
        for (var i=1; i<range_mult * this.params.Wc; i++) {
            this.params.Wp = i-1;
            data_array[i] = [
                this.params.Wp,
                L_crit_SS(this.params),
                L_crit(this.params)
            ];
        }
        var data = google.visualization.arrayToDataTable(data_array);
        this.chart2.draw(data, this.options2);

        this.params.Wp = save_Wp;
    }
}

// Update the plot
function paramBlur()
{
    g.update();
}

function mouseoverHandler(e)
{
    if (e['column'] != 3) {
        // User is not going over the T_G plot
        return;
    }

    var save_wp = g.params.Wp;

    g.params.Wp = parseInt(e['row']);
    document.getElementById("cur_reg").
             firstChild.nodeValue = get_regime(g.params);
    g.params.Wp = save_wp;
}

function in_array(needle, haystack)
{
    return haystack.indexOf(needle) > -1;
}

function keyPressHandler(e)
{
    if (e.keyCode == 13) { //Enter
        g.update();
        return;
    }

    if ((e.keyCode == 36 || e.keyCode == 35) && // Home || End
                        document.activeElement != null) {
        var delta;
        var value;
        var newvalue;

        if (in_array(document.activeElement.id, ["Wp", "Wc", "Sp", "Sc", "Np", "Nc", "L"])) {
            value = parseInt(document.activeElement.value)
            delta = Math.ceil(value/10);
        } else if (in_array(document.activeElement.id, ["Kc", "Kp"])) {
            value = parseInt(document.activeElement.value);
            delta = 1;
        } else {
            return;
        }

        if (delta == 0) {
            delta = 1;
        }

        if (e.keyCode == 36) {
            delta = delta * (-1);
        }
//window.alert("Updated to " + value.toString() + " " + delta.toString());
        newvalue = value + delta;

        if (newvalue < 0) {
            // Don't allow to go negative
            newvalue = value;
        }

        if (newvalue == 0 && !in_array(document.activeElement.id, ["Sc", "Sp", "Np", "Nc"])) {
            // Only some knobs can be tuned to 0
            newvalue = value;
        }

        if (value != newvalue) {
            document.activeElement.value = newvalue.toString()
                g.update();
        }
    }
    // home = 36, end = 35
}

function googleAPILoaded()
{
    g = new Global();
}

// Unused
function onload()
{
}


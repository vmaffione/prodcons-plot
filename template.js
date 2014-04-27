/*
    An old-fashined 60 Hz game.

    Written by Vincenzo Maffione.
*/

/* An object containing all the "global" variables. */
var g;

function resize(x)
{
    x.W = x.canvas.width = x.canvas.parentNode.clientWidth;
    x.H = x.canvas.height = x.canvas.parentNode.clientHeight;
    x.cx = x.W/2;
    x.cy = x.H/2;
}

function getRandInt(max)
{
    return Math.floor(Math.random()*max);
}

function getRandIncr(max)
{
    return Math.floor(Math.random()*max*2 - max);
}

/* Global prototype. */
function Global()
{
    /* Grab the 'canvas' element. */
    this.canvas = document.getElementById("gameCanvas");
    resize(this);

    /* Track the "pressed" state of keyboard keys. */
    this.keys_state = new Array();
    for (var i=0; i<128; i++) {
        this.keys_state[i] = false;
    }

    /* Array of game scenes (just one here). */
    this.scenes = new Array();
    this.scenes[0] = new Game(this);
    this.scene_idx = 0;

    this.next_scene = next_scene;
    function next_scene() {
        if (this.scene_idx >= 0 &&
                this.scene_idx < this.scenes.length) {
            /* It's essential to increment this.scene_idx
               before invoking a start_scene method, otherwise
               unterminated recursion happens. */
            this.scenes[this.scene_idx++].start_scene();
        }
    }
}

function make_rgb_comp(x)
{
    var comp;

    /* Saturation. */
    if (x > 255) {
        x = 255;
    } else if (x < 0) {
        x = 0;
    }

    /* String conversion and formatting. */
    comp = x.toString(16);
    if (comp.length == 1) {
        comp = "0" + comp;
    }

    return comp;
}

function make_rgb(r, g, b)
{
    return "#" + make_rgb_comp(r) + make_rgb_comp(g) + make_rgb_comp(b);
}

function compute_scaling(avail, vec)
{
    var sum = 0;
    var min = vec[0];
    var ratio;

    for (var i = 0; i < vec.length; i++) {
        sum += vec[i];
        if (vec[i] < min) {
            min = vec[i];
        }
    }

    ratio = avail/sum;

    while (ratio * min < 5) {
        ratio *= 1.2;
    }
/*
    while (ratio * min > 100) {
        ratio /= 1.2;
    }*/

    return ratio;
}

/* A prototype representing the game scene. */
function Game(gl)
{
    var y = 80;

    this.gl = gl;

    this.colors = new Array(make_rgb(255, 255, 255), make_rgb(255, 0, 0),
                            make_rgb(0, 255, 0), make_rgb(0, 0, 255));

    durations = new Array();
    types = new Array();
    names = new Array();

    //INSERTDATA
/*
    durations[0] = [4, 2, 6, 2, 2];
    types[0] = [1, 2, 3, 2, 2];
    names[0] = "Producer";

    durations[1] = [6, 4, 3, 3];
    types[1] = [0, 1, 2, 2];
    names[1] = "Consumer";
*/

    scale = compute_scaling(this.gl.W/2, durations[0]);

    /* Array of strips. Each strip represent a task. */
    this.strips = new Array();
    for (var i = 0; i < durations.length; i++) {
        this.strips[i] = new Strip(this, names[i], scale, 20, y,
                                    durations[i], types[i]);
        y += 40;
    }

    this.animation_step = animation_step;
    function animation_step()
    {
        /* Draw everything. */
        this.draw();

        /* Move (update) everything. */
        this.move();
    }

    this.start_scene = start_scene;
    function start_scene()
    {
        var that = this;

        this.timer = setInterval(function() {
                        that.animation_step();
                   }, 1000 / 60);
   }

    this.draw = draw;
    function draw()
    {
        var ctx = this.gl.canvas.getContext("2d");

        /* Draw the background */
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, this.gl.W, this.gl.H);

        /* Draw the strips. */
        for (var i = 0; i < this.strips.length; i++) {
            this.strips[i].draw();
        }

        /* Draw status info. */
        txt = "Status 1: " + 342;
        ctx.font = "16px Arial";
        ctx.fillStyle = '#000000';
        ctx.fillText(txt, 20, 30);
        txt = "Status 2: " + this.gl.W;
        ctx.fillText(txt, 20, 54);

        /* Draw hints. */
        ctx.fillStyle = make_rgb(0, 0, 0);
        ctx.font = "italic 12px Arial";
        txt = "Muovi le frecce per scorrere il tempo";
        txt_width = ctx.measureText(txt).width;
        ctx.fillText(txt, (this.gl.W - txt_width)/2, this.gl.H - 5);
    }

    this.move = move;
    function move()
    {
        for (var i = 0; i < this.strips.length; i++) {
            this.strips[i].move();
        }
    }
}

/* Strip prototype */
function Strip(gm, name, scale, x, y, slicevec_d, slicevec_t)
{
    var slice_x;

    this.gm = gm;
    this.name = name;
    this.x = x;
    this.y = y;
    this.scale = scale;

    slice_x = 0;
    this.slices = new Array();
    for (var j = 0; j < slicevec_d.length; j++) {
        var w;

        /* Width of the i-th slice is proportional. */
        w = scale * slicevec_d[j];
        this.slices[j] = new Slice(this.gm, this.x + slice_x, this.y, w,
                                    slicevec_t[j]);
        slice_x += w;
    }

    this.draw = draw;
    function draw()
    {
        /* Draw each slicee in the strip. */
        for (var i = 0; i < this.slices.length; i++) {
            this.slices[i].draw();
        }
    }

    this.move = move;
    function move()
    {
        for (var i = 0; i < this.slices.length; i++) {
            this.slices[i].move();
        }
    }
}

/* Slice prototype */
function Slice(gm, x, y, w, type)
{
    this.gm = gm;
    this.x = x;
    this.y = y;
    this.w = w;
    this.step = 7;

    this.draw = draw;
    function draw()
    {
        var ctx = this.gm.gl.canvas.getContext("2d");

        ctx.beginPath();
        ctx.rect(this.x, this.y, this.w, 20);

        ctx.fillStyle = this.gm.colors[type];

        if (type != 0)
            ctx.stroke();
        ctx.fill();
    }

    this.move = move;
    function move()
    {
        /* Update the center position. */
/*
        if (this.gm.gl.keys_state[37] && this.cx > 0) {
            this.cx -= this.step;
        }
        if (this.gm.gl.keys_state[38] && this.cy > 0) {
            this.cy -= this.step;
        }
        if (this.gm.gl.keys_state[39] && this.cx < this.gm.gl.W) {
            this.cx += this.step;
        }
        if (this.gm.gl.keys_state[40] && this.cy < this.gm.gl.H) {
            this.cy += this.step;
        }
*/
    }
}

/* Create the global object and start the animation. */
function onload()
{
    g = new Global();

    g.next_scene();
}

/* Record that the key is now not pressed. */
function bodyKeyUp(e)
{
    g.keys_state[e.keyCode] = false;
}

/* Record that the key is now pressed. */
function bodyKeyDown(e)
{
    g.keys_state[e.keyCode] = true;
}

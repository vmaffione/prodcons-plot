#include <iostream>
#include <list>
#include <queue>
#include <algorithm>
#include <string>
#include <iomanip>
#include <fstream>
#include <fstream>
#include <cassert>
#include <unistd.h>
#include <cstring>

using namespace std;



class Scheduler;

class State {
    public:
        virtual void print() const = 0;
        virtual ~State() { }
};

class Work {
    public:
        /* How much this work takes to complete. */
        double delta;
        /* The scheduler which is going to schedule this work. */
        Scheduler *sched;
        /* Shared state the work is going to operate on. */
        State *state;

        Work() : delta(0.0), sched(NULL), state(NULL) { }
        Work(double d, Scheduler *s, State *st) :
                            delta(d), sched(s), state(st) { }

        /* Action executed when the work gets completed. */
        virtual void action() { }
        virtual string name() const = 0;
        virtual unsigned int type() const = 0;
};

class SchedulerEvent {
    public:
        /* True if this event represent a work completion, false if
           it represent a work start. */
        bool end;
        /* What time the work 'w' completes. */
        double ts;
        /* What thread executes 'w'. */
        unsigned int thread;
        /* The wrapped work (owned reference). */
        Work *w;

        SchedulerEvent() { }
        SchedulerEvent(double _ts, unsigned int _th, bool _end, Work *_w) :
                                    ts(_ts), thread(_th), end(_end), w(_w) { }
};

class SchedulerEventGreater {
    public:
        bool operator()(const SchedulerEvent& e1, const SchedulerEvent& e2) {
            return e1.ts > e2.ts;
        }
};

struct Slice {
    double duration;
    unsigned int type;

    Slice(double d, unsigned int t) : duration(d), type(t) { }
};

class Scheduler {
        /* What time a thread is going to be idle again. */
        double *next_idle_ts;
        /* Current simulation time. */
        double t;
        /* A queue containing the work to be scheduled, sorted in ascending
           work completion time. */
        list<SchedulerEvent> eventq;

        /* Number of threads managed by this scheduler. */
        unsigned int nthreads;
        unsigned int ntypes;

        list<Slice> *strips;

        bool verbose;

        void push_event(SchedulerEvent);
        SchedulerEvent pop_event();

    public:
        string *threadnames;
        string *typenames;

        Scheduler(unsigned int nth, unsigned int nty, bool vb);
        void scheduleWork(unsigned int thread, Work *w);
        void run(double max_time);
        void diagrams(const char *file);
        ~Scheduler();
};

Scheduler::Scheduler(unsigned int nth, unsigned int nty, bool vb) :
                        t(0.0), nthreads(nth), ntypes(nty), verbose(vb)
{
    next_idle_ts = new double[nthreads];
    threadnames = new string[nthreads];
    typenames = new string[ntypes];
    strips = new list<Slice>[nthreads];

    for (unsigned int i = 0; i < nthreads; i++) {
        next_idle_ts[i] = 0.0;
    }
}

Scheduler::~Scheduler()
{
    delete [] next_idle_ts;
    delete [] threadnames;
    delete [] typenames;
    delete [] strips;
}

void Scheduler::push_event(SchedulerEvent se)
{
    list<SchedulerEvent>::reverse_iterator lit = eventq.rbegin();
    list<SchedulerEvent>::iterator nit;

    while (lit != eventq.rend() && se.ts < lit->ts) {
        lit++;
    }

    nit = lit.base();
    eventq.insert(nit, se);
}

SchedulerEvent Scheduler::pop_event()
{
    SchedulerEvent se = eventq.front();

    eventq.pop_front();

    return se;
}

void Scheduler::scheduleWork(unsigned int thread, Work *w)
{
    double begin_ts, end_ts;

    assert(w && thread < nthreads);

    if (next_idle_ts[thread] < t) {
        strips[thread].push_back(Slice(t - next_idle_ts[thread], 0));
    }

    begin_ts = std::max(next_idle_ts[thread], t);
    end_ts = begin_ts + w->delta;
    /* Schedule the events associated to the work begin and end. */
    push_event(SchedulerEvent(begin_ts, thread, false, w));
    push_event(SchedulerEvent(end_ts, thread, true, w));
    next_idle_ts[thread] = end_ts;
    strips[thread].push_back(Slice(w->delta, w->type()));
}

void Scheduler::run(double max_time)
{
    SchedulerEvent sw;

    /* Reset the scheduler time. */
    t = 0;

    while (!eventq.empty() && t <= max_time) {
        sw = pop_event();

        /* Advance the simulation time. */
        t = sw.ts;

        if (verbose) {
            cout << "t = " << t << ": " << sw.w->name() << " ";
            if (sw.end) {
                cout << "ends\n";
            } else {
                cout << "starts\n";
            }
        }

        if (sw.end) {
            /* Execute the completion action. */
            sw.w->action();

            /* Delete the work object, since it is not needed anymore. */
            delete sw.w;
        }
    }
}

void cat(const char *in, ofstream& fout)
{
    ifstream fin(in);

    if (fin.fail()) {
        perror("cat()");
        exit(EXIT_FAILURE);
    }

    for (;;) {
        string s;

        getline(fin, s);

        if (fin.eof() || fin.fail() || fin.bad()) {
            break;
        }

        fout << s << "\n";
    }
}

void Scheduler::diagrams(const char *file)
{
    ifstream fin("template.js");
    ofstream fout(file);

    if (fin.fail()) {
        perror("diagrams()");
        exit(EXIT_FAILURE);
    }

    cat("template_head.html", fout);

    for (;;) {
        string s;

        getline(fin, s);

        if (fin.eof() || fin.fail() || fin.bad()) {
            break;
        }

        if (s.find("//INSERTDATA") != string::npos) {
            for (unsigned int i = 0; i < nthreads; i++) {
                fout << "   durations[" << i << "] = [";
                for (list<Slice>::iterator lit = strips[i].begin();
                                            lit != strips[i].end(); lit++) {
                    fout << lit->duration << ", ";
                }
                fout << "];\n";

                fout << "   types[" << i << "] = [";
                for (list<Slice>::iterator lit = strips[i].begin();
                                            lit != strips[i].end(); lit++) {
                    fout << lit->type << ", ";
                }
                fout << "];\n";

                fout << "   threadnames[" << i << "] = \"" << threadnames[i] << "\";\n";
            }

            fout << "   this.typenames = [";
            for (unsigned int i = 0; i < ntypes; i++) {
                fout << "\"" << typenames[i] << "\", ";
            }
            fout << "];\n";

        } else {
            fout << s << "\n";
        }
    }

    cat("template_tail.html", fout);
}


#define PROD_TH         0
#define CONS_TH         1
static double L  = 32;
static double SP = 3.0;
static double NP = 4.0;
static double WP = 10.0;
static double SC = 3.0;
static double NC = 4.0;
static double WC = 13.0;
static double T  = 100.0;

static const char *outname = "output.html";

#define TNULL           0
#define TSTART          1
#define TNOTIFY         2
#define TPROCESS        3

class ProdConState : public State {
    public:
        /* Statistics. */
        unsigned int prod_proc;
        unsigned int prod_ntfy;
        unsigned int cons_proc;
        unsigned int cons_ntfy;

        /* Shared state. */
        unsigned int queue_len;
        bool prod_idle;
        bool cons_idle;

        ProdConState();
        virtual void print() const;
};

ProdConState::ProdConState()
{
    prod_proc = prod_ntfy = 0;
    cons_proc = cons_ntfy = 0;

    queue_len = 0;
    prod_idle = cons_idle = true;
}

void ProdConState::print() const
{
    cout << "Statistics:\n";
    cout << "   producer.processed     = " << prod_proc << "\n";
    cout << "   consumer.processed     = " << cons_proc << "\n";
    cout << "   producer.notifications = " << prod_ntfy << "\n";
    cout << "   consumer.notifications = " << cons_ntfy << "\n";
}

class ProducerStartWork : public Work {
    public:
        ProducerStartWork(Scheduler *sched, State *state) :
                                        Work(SP, sched, state) { }
        virtual void action();
        virtual string name() const { return "ProducerStart"; }
        virtual unsigned int type() const { return TSTART; }
};

class ProducerProcessWork : public Work {
    public:
        ProducerProcessWork(Scheduler *sched, State *state) :
                                        Work(WP, sched, state) { }
        virtual void action();
        virtual string name() const { return "ProducerProcess"; }
        virtual unsigned int type() const { return TPROCESS; }
};

class ProducerNotifyWork : public Work {
    public:
        ProducerNotifyWork(Scheduler *sched, State *state) :
                                        Work(NP, sched, state) { }
        virtual void action();
        virtual string name() const { return "ProducerNotify"; }
        virtual unsigned int type() const { return TNOTIFY; }
};

class ConsumerStartWork : public Work {
    public:
        ConsumerStartWork(Scheduler *sched, State *state) :
                                        Work(SC, sched, state) { }
        virtual void action();
        virtual string name() const { return "ConsumerStart"; }
        virtual unsigned int type() const { return TSTART; }
};

class ConsumerProcessWork : public Work {
    public:
        ConsumerProcessWork(Scheduler *sched, State *state) :
                                        Work(WC, sched, state) { }
        virtual void action();
        virtual string name() const { return "ConsumerProcess"; }
        virtual unsigned int type() const { return TPROCESS; }
};

class ConsumerNotifyWork : public Work {
    public:
        ConsumerNotifyWork(Scheduler *sched, State *state) :
                                        Work(NC, sched, state) { }
        virtual void action();
        virtual string name() const { return "ConsumerNotify"; }
        virtual unsigned int type() const { return TNOTIFY; }
};

void ProducerStartWork::action()
{
    ProdConState *st = dynamic_cast<ProdConState *>(state);

    if (st->queue_len < L) {
        st->prod_idle = false;
        sched->scheduleWork(PROD_TH, new ProducerProcessWork(sched, state));
    }
}

void ProducerProcessWork::action()
{
    ProdConState *st = dynamic_cast<ProdConState *>(state);

    st->prod_proc++;
    st->queue_len++;

    if (st->cons_idle) {
        sched->scheduleWork(PROD_TH, new ProducerNotifyWork(sched, state));
    }

    if (st->queue_len < L) {
        sched->scheduleWork(PROD_TH, new ProducerProcessWork(sched, state));
    } else {
        st->prod_idle = true;
    }
}

void ProducerNotifyWork::action()
{
    ProdConState *st = dynamic_cast<ProdConState *>(state);

    st->prod_ntfy++;
    sched->scheduleWork(CONS_TH, new ConsumerStartWork(sched, state));
}

void ConsumerStartWork::action()
{
    ProdConState *st = dynamic_cast<ProdConState *>(state);

    if (st->queue_len) {
        st->cons_idle = false;
        sched->scheduleWork(CONS_TH, new ConsumerProcessWork(sched, state));
    }
}

void ConsumerProcessWork::action()
{
    ProdConState *st = dynamic_cast<ProdConState *>(state);

    st->cons_proc++;
    st->queue_len--;

    if (st->prod_idle) {
        sched->scheduleWork(CONS_TH, new ConsumerNotifyWork(sched, state));
    }

    if (st->queue_len) {
        sched->scheduleWork(CONS_TH, new ConsumerProcessWork(sched, state));
    } else {
        st->cons_idle = true;
    }
}

void ConsumerNotifyWork::action()
{
    ProdConState *st = dynamic_cast<ProdConState *>(state);

    st->cons_ntfy++;
    sched->scheduleWork(PROD_TH, new ProducerStartWork(sched, state));
}

static void help()
{
    cout << "Options:\n";
    cout << "   -s TICKS    --  Producer Start\n";
    cout << "   -n TICKS    --  Producer Notify\n";
    cout << "   -w TICKS    --  Producer Process\n";
    cout << "   -S TICKS    --  Consumer Start\n";
    cout << "   -N TICKS    --  Consumer Notify\n";
    cout << "   -W TICKS    --  Consumer Process\n";
    cout << "   -T NUM      --  Simulation length = NUM * WC\n";
    cout << "   -L NUM      --  Queue length\n";
    cout << "   -o FILENAME --  HTML output name\n";
    cout << "   -O          --  no HTML output file\n";
}

static double safe_atof(char *optarg)
{
    int x = atoi(optarg);

    if (x < 1) {
        x = 1;
    }

    return static_cast<double>(x);
}

static void parse_args(int argc, char **argv)
{
    int c;
    int x;

    while ((c = getopt(argc, argv, "s:n:w:S:N:W:T:t:L:l:Oh")) != -1) {
        switch (c) {
            case 's':
                SP = safe_atof(optarg);
                break;

            case 'n':
                NP = safe_atof(optarg);
                break;

            case 'w':
                WP = safe_atof(optarg);
                break;

            case 'S':
                SC = safe_atof(optarg);
                break;

            case 'N':
                NC = safe_atof(optarg);
                break;

            case 'W':
                WC = safe_atof(optarg);
                break;

            case 'T':
            case 't':
                T = safe_atof(optarg);
                break;

            case 'L':
            case 'l':
                L = safe_atof(optarg);
                break;

            case 'o':
                outname = strdup(optarg);
                break;

            case 'O':
                outname = NULL;
                break;

            case 'h':
                help();
                exit(EXIT_SUCCESS);

            default:
                help();
                exit(EXIT_FAILURE);
        }
    }

    cout << "Parameters used:\n";
    cout << "   SP = " << SP << "\n";
    cout << "   NP = " << NP << "\n";
    cout << "   WP = " << WP << "\n";
    cout << "   SC = " << SC << "\n";
    cout << "   NC = " << NC << "\n";
    cout << "   WC = " << WC << "\n";
    cout << "   L  = " << L  << "\n";
    cout << "   T  = " << T  << "\n";
}

int main(int argc, char **argv)
{
    /* Two threads, four types, not verbose. */
    Scheduler sched(2, 4, false);
    ProdConState *state = new ProdConState();
    double result = 0.0;

    parse_args(argc, argv);

    /* Give names to the threads. */
    sched.threadnames[PROD_TH] = "Producer";
    sched.threadnames[CONS_TH] = "Consumer";

    /* Give names to the work types. */
    sched.typenames[TNULL] = "Null";
    sched.typenames[TSTART] = "Start";
    sched.typenames[TNOTIFY] = "Notify";
    sched.typenames[TPROCESS] = "Process";

    /* Schedule the initial work (kick the producer). */
    sched.scheduleWork(PROD_TH, new ProducerStartWork(&sched, state));

    /* Run the simulation. */
    sched.run(T * WC);

    /* Print some statistics. */
    state->print();

    /* Print the simulation result. */
    if (state->cons_proc) {
        result = T * WC / state->cons_proc;
    }
    cout << "Average-time-per-slot = " << result << "\n";

    /* Produce HTML output. */
    if (outname) {
        sched.diagrams(outname);
    }

    return 0;
}

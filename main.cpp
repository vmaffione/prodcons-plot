#include <iostream>
#include <list>
#include <queue>
#include <algorithm>
#include <string>
#include <iomanip>
#include <cassert>

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

class Scheduler {
        /* What time a thread is going to be idle again. */
        double *next_idle_ts;
        /* Current simulation time. */
        double t;
        /* A queue containing the work to be scheduled, sorted in ascending work
           completion time. */
        priority_queue< SchedulerEvent, vector<SchedulerEvent>,
                        SchedulerEventGreater > eventq;
        /* Number of threads managed by this scheduler. */
        unsigned int nthreads;

    public:

        Scheduler(unsigned int n);
        void scheduleWork(unsigned int thread, Work *w);
        void run(double max_time);
        ~Scheduler();
};

Scheduler::Scheduler(unsigned int n) : t(0.0), nthreads(n)
{
    next_idle_ts = new double[n];

    for (unsigned int i = 0; i < n; i++) {
        next_idle_ts[i] = 0.0;
    }
}

Scheduler::~Scheduler()
{
    delete next_idle_ts;
}

void Scheduler::scheduleWork(unsigned int thread, Work *w)
{
    double begin_ts, end_ts;

    assert(w && thread < nthreads);

    begin_ts = std::max(next_idle_ts[thread], t);
    end_ts = begin_ts + w->delta;
    /* Schedule the events associated to the work begin and end. */
    eventq.push(SchedulerEvent(begin_ts, thread, false, w));
    eventq.push(SchedulerEvent(end_ts, thread, true, w));
    next_idle_ts[thread] = end_ts;
}

void Scheduler::run(double max_time)
{
    SchedulerEvent sw;

    /* Reset the scheduler time. */
    t = 0;

    while (!eventq.empty() && t <= max_time) {
        sw = eventq.top();
        eventq.pop();

        /* Advance the simulation time. */
        t = sw.ts;

        cout << "t = " << t << ": " << sw.w->name() << " ";
        if (sw.end) {
            cout << "ends\n";
        } else {
            cout << "starts\n";
        }

        if (sw.end) {
            /* Execute the completion action. */
            sw.w->action();

            /* Delete the work object, since it is not needed anymore. */
            delete sw.w;
        }
    }
}

#define PROD_TH         0
#define CONS_TH         1
#define SP              3.0
#define NP              10.0
#define WP              2.0
#define SC              3.0
#define NC              10.0
#define WC              3.0
#define QUEUE_LEN_MAX   256

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
    cout << "producer.processed     = " << prod_proc << "\n";
    cout << "consumer.processed     = " << cons_proc << "\n";
    cout << "producer.notifications = " << prod_ntfy << "\n";
    cout << "consumer.notifications = " << cons_ntfy << "\n";
}

class ProducerStartWork : public Work {
    public:
        ProducerStartWork(Scheduler *sched, State *state) :
                                        Work(SP, sched, state) { }
        virtual void action();
        virtual string name() const { return "ProducerStart"; }
};

class ProducerProcessWork : public Work {
    public:
        ProducerProcessWork(Scheduler *sched, State *state) :
                                        Work(WP, sched, state) { }
        virtual void action();
        virtual string name() const { return "ProducerProcess"; }
};

class ProducerNotifyWork : public Work {
    public:
        ProducerNotifyWork(Scheduler *sched, State *state) :
                                        Work(NP, sched, state) { }
        virtual void action();
        virtual string name() const { return "ProducerNotify"; }
};

class ConsumerStartWork : public Work {
    public:
        ConsumerStartWork(Scheduler *sched, State *state) :
                                        Work(SC, sched, state) { }
        virtual void action();
        virtual string name() const { return "ConsumerStart"; }
};

class ConsumerProcessWork : public Work {
    public:
        ConsumerProcessWork(Scheduler *sched, State *state) :
                                        Work(WC, sched, state) { }
        virtual void action();
        virtual string name() const { return "ConsumerProcess"; }
};

class ConsumerNotifyWork : public Work {
    public:
        ConsumerNotifyWork(Scheduler *sched, State *state) :
                                        Work(NC, sched, state) { }
        virtual void action();
        virtual string name() const { return "ConsumerNotify"; }
};

void ProducerStartWork::action()
{
    ProdConState *st = dynamic_cast<ProdConState *>(state);

    if (st->queue_len < QUEUE_LEN_MAX) {
        st->prod_idle = false;
        sched->scheduleWork(PROD_TH, new ProducerProcessWork(sched, state));
    }
}

void ProducerProcessWork::action()
{
    ProdConState *st = dynamic_cast<ProdConState *>(state);

    st->prod_proc++;
    st->queue_len++;

    if (st->queue_len < QUEUE_LEN_MAX) {
        sched->scheduleWork(PROD_TH, new ProducerProcessWork(sched, state));
    } else {
        st->prod_idle = true;
    }

    if (st->cons_idle) {
        sched->scheduleWork(PROD_TH, new ProducerNotifyWork(sched, state));
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

    if (st->queue_len) {
        sched->scheduleWork(CONS_TH, new ConsumerProcessWork(sched, state));
    } else {
        st->cons_idle = true;
    }

    if (st->prod_idle) {
        sched->scheduleWork(CONS_TH, new ConsumerNotifyWork(sched, state));
    }
}

void ConsumerNotifyWork::action()
{
    ProdConState *st = dynamic_cast<ProdConState *>(state);

    st->cons_ntfy++;
    sched->scheduleWork(PROD_TH, new ProducerStartWork(sched, state));
}

int main()
{
    Scheduler sched(2);
    ProdConState *state = new ProdConState();

    sched.scheduleWork(PROD_TH, new ProducerStartWork(&sched, state));

    sched.run(100 * WC);

    cout << "\n>>> Simulation completed\n";
    state->print();

    return 0;
}

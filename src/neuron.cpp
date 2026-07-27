#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <set>
#include <string>
#include <tuple>
#include <vector>

struct Neuron {
    double v=-65.0, adaptation=0.0;
    int refractory=0;
    bool spiked=false;
};

struct Result {
    int winner=0;
    double top=0.0, second=0.0, margin=0.0, entropy=0.0, total=0.0;
    std::vector<double> activity;
};

class SNN {
    int ni_, nh_, no_;
    std::vector<Neuron> h_, o_;
    std::vector<double> ht_, ot_, htr_, otr_;
    std::vector<std::vector<double>> wih_, who_;
    double lr_=0.025;
    std::mt19937_64 rng_;
    static double clamp(double x,double a,double b){return std::max(a,std::min(x,b));}

    void reset_state(){
        for(auto &n:h_) n=Neuron{};
        for(auto &n:o_) n=Neuron{};
        std::fill(htr_.begin(),htr_.end(),0.0);
        std::fill(otr_.begin(),otr_.end(),0.0);
    }
    void step_neuron(Neuron& n,double in,double th){
        n.spiked=false;
        if(n.refractory>0){--n.refractory; n.v+=0.30*(-70.0-n.v); n.adaptation*=0.96; return;}
        n.v += -0.08*(n.v+65.0)+in-0.10*n.adaptation;
        n.v=clamp(n.v,-80.0,20.0);
        if(n.v>=th){n.spiked=true;n.v=-70.0;n.refractory=3;n.adaptation+=1.2;}
        n.adaptation*=0.96;
    }
    void normalise(){
        for(int j=0;j<nh_;++j){double n=0;for(int i=0;i<ni_;++i)n+=wih_[i][j]*wih_[i][j];n=std::sqrt(n)+1e-12;if(n>3.5)for(int i=0;i<ni_;++i)wih_[i][j]*=3.5/n;}
        for(int k=0;k<no_;++k){double n=0;for(int j=0;j<nh_;++j)n+=who_[j][k]*who_[j][k];n=std::sqrt(n)+1e-12;if(n>4.0)for(int j=0;j<nh_;++j)who_[j][k]*=4.0/n;}
    }
public:
    SNN(int ni=9,int nh=18,int no=9,std::uint64_t seed=1):ni_(ni),nh_(nh),no_(no),h_(nh),o_(no),ht_(nh,-50),ot_(no,-50),htr_(nh),otr_(no),wih_(ni,std::vector<double>(nh)),who_(nh,std::vector<double>(no)),rng_(seed){
        std::normal_distribution<double> a(0.90,0.25),b(0.70,0.30);std::bernoulli_distribution inh(0.20);
        for(auto& r:wih_)for(double& x:r)x=clamp(a(rng_),0.2,1.6);
        for(auto& r:who_)for(double& x:r){double m=clamp(std::abs(b(rng_)),0.15,1.5);x=inh(rng_)?-m:m;}
    }
    void forward(const std::vector<double>& in){
        for(int j=0;j<nh_;++j){double cur=0;for(int i=0;i<ni_;++i)cur+=in[i]*wih_[i][j];step_neuron(h_[j],0.42*cur,ht_[j]);htr_[j]*=0.82;if(h_[j].spiked)htr_[j]+=1.0;}
        for(int k=0;k<no_;++k){double cur=0;for(int j=0;j<nh_;++j)cur+=htr_[j]*who_[j][k];step_neuron(o_[k],0.62*cur,ot_[k]);otr_[k]*=0.90;if(o_[k].spiked)otr_[k]+=1.0;}
    }
    Result test(const std::vector<double>& in,int steps=80){
        reset_state();for(int t=0;t<steps;++t)forward(in);
        Result r;r.activity=otr_;r.total=std::accumulate(otr_.begin(),otr_.end(),0.0);
        std::vector<double> s=otr_;std::sort(s.begin(),s.end(),std::greater<double>());r.top=s[0];r.second=s.size()>1?s[1]:0;r.margin=r.top-r.second;
        r.winner=int(std::distance(otr_.begin(),std::max_element(otr_.begin(),otr_.end())));
        if (r.total > 1e-12) {
            for (double x : otr_) {
                const double probability = x / r.total;
                if (probability > 1e-12) {
                    r.entropy -= probability * std::log(probability);
                }
            }
        }
        return r;
    }
    void train_competitive(const std::vector<double>& in,int target,int steps){
        reset_state();
        for(int t=0;t<steps;++t){
            forward(in);
            int win=target;
            for(int i=0;i<ni_;++i)for(int j=0;j<nh_;++j){if(in[i]>0.3&&h_[j].spiked)wih_[i][j]+=lr_*in[i]*0.025;else wih_[i][j]*=0.99998;wih_[i][j]=clamp(wih_[i][j],0.02,2.5);}
            for (int j = 0; j < nh_; ++j) {
                for (int k = 0; k < no_; ++k) {
                    if (htr_[j] > 0.2) {
                        if (k == win) {
                            who_[j][k] += lr_ * htr_[j] * 0.045;
                        } else if (otr_[k] > 0.01) {
                            who_[j][k] -= lr_ * htr_[j] * 0.014;
                        }
                    }
                    who_[j][k] *= 0.99998;
                    who_[j][k] = clamp(who_[j][k], -2.5, 2.5);
                }
            }
            normalise();
        }
    }
    void mutate(double strength){
        std::normal_distribution<double> d(0.0,strength);lr_=clamp(lr_*std::exp(d(rng_)*0.15),0.002,0.08);
        for (double& x : ht_) {
            x = clamp(x + d(rng_) * 0.15, -56.0, -46.0);
        }
        for (double& x : ot_) {
            x = clamp(x + d(rng_) * 0.20, -56.0, -45.0);
        }
        for (auto& row : wih_) {
            for (double& x : row) {
                x = clamp(x + d(rng_) * 0.015, 0.02, 2.5);
            }
        }
        for (auto& row : who_) {
            for (double& x : row) {
                x = clamp(x + d(rng_) * 0.020, -2.5, 2.5);
            }
        }
        normalise();
    }
};

static std::vector<std::vector<double>> make_patterns(int n,int dims,std::mt19937_64& rng){
    std::vector<std::vector<double>> p;std::uniform_int_distribution<int> idx(0,dims-1);std::uniform_real_distribution<double> amp(2.4,3.5);
    for(int q=0;q<n;++q){std::vector<double> x(dims,0.0);int a=idx(rng),b=idx(rng);while(b==a)b=idx(rng);x[a]=amp(rng);x[b]=amp(rng);p.push_back(x);}return p;
}
static std::vector<double> noisy(const std::vector<double>& x,double sigma,std::mt19937_64& rng){std::normal_distribution<double>d(0,sigma);auto y=x;for(double&v:y)v=std::max(0.0,std::min(5.0,v+d(rng)));return y;}

struct Eval {
    double avg_margin=0,min_margin=0,avg_entropy=0;
    double noise_consistency=0,target_acc=0,noise_target_acc=0;
    double retention=0,usage_entropy=0;
    int distinct=0;
    std::vector<int>winners;
};
static Eval evaluate(SNN& net,const std::vector<std::vector<double>>& p,
                     const std::vector<int>* reference,std::uint64_t noise_seed){
    Eval e;
    std::set<int> uniq;
    std::vector<int> usage(9,0);
    e.min_margin=std::numeric_limits<double>::infinity();

    for(size_t pi=0;pi<p.size();++pi){
        const auto& x=p[pi];
        const int target=int(pi%9);
        auto r=net.test(x);
        e.avg_margin+=r.margin;
        e.min_margin=std::min(e.min_margin,r.margin);
        e.avg_entropy+=r.entropy;
        e.winners.push_back(r.winner);
        uniq.insert(r.winner);
        if(r.winner>=0&&r.winner<9)++usage[r.winner];
        e.target_acc += (r.winner==target);

        int same_clean=0, correct_target=0;
        for(int k=0;k<16;++k){
            std::mt19937_64 local_rng(noise_seed + 0x9E3779B97F4A7C15ULL*(pi+1) + 0xBF58476D1CE4E5B9ULL*(k+1));
            const int noisy_winner=net.test(noisy(x,0.18,local_rng)).winner;
            same_clean += noisy_winner==r.winner;
            correct_target += noisy_winner==target;
        }
        e.noise_consistency+=double(same_clean)/16.0;
        e.noise_target_acc+=double(correct_target)/16.0;
    }

    if(!p.empty()){
        const double n=double(p.size());
        e.avg_margin/=n;
        e.avg_entropy/=n;
        e.noise_consistency/=n;
        e.target_acc/=n;
        e.noise_target_acc/=n;
        for(int c:usage){
            if(c){
                const double q=double(c)/n;
                e.usage_entropy-=q*std::log(q);
            }
        }
        const double denom=std::log(double(std::max(2,std::min<int>(9,p.size()))));
        if(denom>0)e.usage_entropy/=denom;
    }else{
        e.min_margin=0;
    }
    e.distinct=int(uniq.size());

    if(reference&&!reference->empty()){
        int same=0;
        for(size_t i=0;i<e.winners.size()&&i<reference->size();++i)
            same+=e.winners[i]==(*reference)[i];
        e.retention=double(same)/std::min(e.winners.size(),reference->size());
    }
    return e;
}

static double objective(const Eval&e,int patterns){
    const int capacity=std::max(1,std::min(patterns,9));
    const double diversity=double(e.distinct)/capacity;
    const double margin=std::clamp(e.avg_margin,0.0,1.0);
    const double min_margin=std::clamp(e.min_margin,0.0,1.0);
    const double entropy_quality=1.0/(1.0+std::abs(e.avg_entropy-1.1));

    double score=
        0.20*e.target_acc+
        0.22*e.noise_target_acc+
        0.10*e.noise_consistency+
        0.12*margin+
        0.08*min_margin+
        0.12*diversity+
        0.12*e.usage_entropy+
        0.04*entropy_quality;

    const int required=std::max(2,(capacity+1)/2);
    if(e.distinct<required)score*=double(e.distinct)/required;
    if(e.distinct==1)score*=0.05;
    if(e.target_acc<0.25)score*=0.50;
    return score;
}

int main(int argc,char**argv){
    int patterns=8,epochs=12,train_steps=90,mutations=220,seeds=24;
    if(argc>1)patterns=std::max(2,std::stoi(argv[1]));

    std::ofstream csv("research_results_v5.csv");
    csv<<"seed,initial,trained,evolved,train_delta,evolve_delta,total_delta,target_acc,noise_target_acc,noise_consistency,avg_margin,min_margin,distinct,usage_entropy,retention,flag\n";

    double best_quality=-1e9;
    int best_seed=-1;
    Eval best_eval;
    std::vector<int> best_map;

    for(int seed=1;seed<=seeds;++seed){
        const std::uint64_t eval_seed=0xD1B54A32D192ED03ULL + std::uint64_t(seed)*7919ULL;
        std::mt19937_64 pattern_rng(seed*7919ULL);
        auto p=make_patterns(patterns,9,pattern_rng);
        SNN net(9,18,9,seed);

        Eval initial_eval=evaluate(net,p,nullptr,eval_seed);
        const double initial_score=objective(initial_eval,patterns);

        std::vector<int> order(patterns);
        std::iota(order.begin(),order.end(),0);
        std::mt19937_64 train_rng(0xA0761D6478BD642FULL + std::uint64_t(seed));
        SNN best_trained=net;
        double best_train_score=initial_score;

        for(int e=0;e<epochs;++e){
            std::shuffle(order.begin(),order.end(),train_rng);
            const double sigma=0.03+0.015*e;
            for(int pi:order){
                const int target=pi%9;
                net.train_competitive(p[pi],target,train_steps);
                for(int a=0;a<3;++a){
                    std::mt19937_64 aug_rng(eval_seed + 1000003ULL*std::uint64_t(e+1) + 1009ULL*std::uint64_t(pi+1) + std::uint64_t(a));
                    net.train_competitive(noisy(p[pi],sigma,aug_rng),target,train_steps/3);
                }
            }
            Eval checkpoint=evaluate(net,p,nullptr,eval_seed);
            const double checkpoint_score=objective(checkpoint,patterns);
            if(checkpoint_score>best_train_score){
                best_train_score=checkpoint_score;
                best_trained=net;
            }else if(checkpoint_score<0.85*best_train_score){
                net=best_trained;
            }
        }
        net=best_trained;

        Eval trained_eval=evaluate(net,p,nullptr,eval_seed);
        const std::vector<int> reference=trained_eval.winners;
        const double trained_score=objective(trained_eval,patterns);

        SNN best=net;
        double best_score=trained_score;
        for(int m=0;m<mutations;++m){
            SNN candidate=best;
            candidate.mutate(std::max(0.05,0.35*std::pow(0.985,m)));
            Eval candidate_eval=evaluate(candidate,p,&reference,eval_seed);
            const double candidate_score=objective(candidate_eval,patterns);
            if(candidate_score>best_score+1e-12){
                best_score=candidate_score;
                best=candidate;
            }
        }

        net=best;
        Eval evolved_eval=evaluate(net,p,&reference,eval_seed);
        const double evolved_score=objective(evolved_eval,patterns);

        const double train_delta=trained_score-initial_score;
        const double evolve_delta=evolved_score-trained_score;
        const double total_delta=evolved_score-initial_score;

        const int flag_distinct=std::min(patterns,6);
        const bool flag=evolved_eval.distinct>=flag_distinct &&
                        evolved_eval.usage_entropy>=0.75 &&
                        evolved_eval.target_acc>=0.75 &&
                        evolved_eval.noise_target_acc>=0.70 &&
                        evolved_eval.avg_margin>=0.25 &&
                        evolved_eval.min_margin>=0.05 &&
                        evolved_eval.retention>=0.75;

        csv<<seed<<','<<initial_score<<','<<trained_score<<','<<evolved_score<<','
           <<train_delta<<','<<evolve_delta<<','<<total_delta<<','
           <<evolved_eval.target_acc<<','<<evolved_eval.noise_target_acc<<','
           <<evolved_eval.noise_consistency<<','<<evolved_eval.avg_margin<<','
           <<evolved_eval.min_margin<<','<<evolved_eval.distinct<<','
           <<evolved_eval.usage_entropy<<','<<evolved_eval.retention<<','
           <<(flag?1:0)<<'\n';

        std::cout<<"seed="<<std::setw(2)<<seed
                 <<" initial="<<std::fixed<<std::setprecision(3)<<initial_score
                 <<" trained="<<trained_score
                 <<" evolved="<<evolved_score
                 <<" train_d="<<train_delta
                 <<" evolve_d="<<evolve_delta
                 <<" target="<<evolved_eval.target_acc
                 <<" noisy_target="<<evolved_eval.noise_target_acc
                 <<" consistency="<<evolved_eval.noise_consistency
                 <<" margin="<<evolved_eval.avg_margin
                 <<" min="<<evolved_eval.min_margin
                 <<" distinct="<<evolved_eval.distinct
                 <<" usageH="<<evolved_eval.usage_entropy
                 <<" retention="<<evolved_eval.retention
                 <<(flag?"  [UNUSUAL]":"")<<'\n';

        if(evolved_score>best_quality){
            best_quality=evolved_score;
            best_seed=seed;
            best_eval=evolved_eval;
            best_map=evolved_eval.winners;
        }
    }

    std::cout<<"\nBest final-quality run seed="<<best_seed
             <<" score="<<best_quality<<"\nPattern -> motor: ";
    for(size_t i=0;i<best_map.size();++i)std::cout<<i<<"->"<<best_map[i]<<' ';
    std::cout<<"\nMetrics: target_accuracy="<<best_eval.target_acc
             <<" noisy_target_accuracy="<<best_eval.noise_target_acc
             <<" noise_consistency="<<best_eval.noise_consistency
             <<" avg_margin="<<best_eval.avg_margin
             <<" min_margin="<<best_eval.min_margin
             <<" distinct="<<best_eval.distinct
             <<" usage_entropy="<<best_eval.usage_entropy
             <<" retention="<<best_eval.retention<<"\n";
    std::cout<<"CSV written to research_results_v5.csv\n";
    std::cout<<"Version 5 adds a deterministic noise curriculum, best-epoch rollback, target accuracy, and noisy-target accuracy.\n";
    std::cout<<"Pseudo-labels test representational capacity; they do not demonstrate unsupervised concept discovery. An [UNUSUAL] flag is only a harness threshold.\n";
}

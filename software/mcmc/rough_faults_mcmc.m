%% induced seismicity fault orientations

%% Load the data
T = load('fault_orientations.mat');
obs_dist = T.fault_orientations.Azimuth_deg - nanmean(T.fault_orientations.Azimuth_deg);

figure; 
histogram(obs_dist)
title('Observed distribution')

%% set up MCMC

% **NUMBER OF ITERATIONS**
Niter = 1e3; % this is low, but it will work while your testing; this is the number of steps the MCMC algorithm takes

% **RATE OF SAMPLES KEPT**
k = 10; 

% **NUMBER OF BURN-IN SAMPLES**
bcut = 0; % set to zero to view the burn-in period

% **WRITE OUTPUT TO FILE**
% recommended for large runs
write_flag = true;

% **INITIAL X**
% x0 [gamma, log10(alpha), friction coefficient]
x = [0.8, -2.5, 0.75]'; 

% **STEPSIZE 
stepsize = 0.2;

% **BOUNDS**
lb = zeros(size(x)); lb(2) = -4; lb(3) = 0.6;
ub = [1, 0, 0.8]'; % the bounds for alpha are log10(alpha)
bounds = [lb, ub]; 

% runtime/likelihood function parameters
A = [];
b = [];

% set the number of simulations inside the function 
% this is the number of psis to randomly draw, could be less
Nsim = 2e3; 

% run mcmc
mcmc(Niter, stepsize, @likelihood_01, x, k, bounds, A, b, bcut, write_flag, obs_dist, Nsim);

if write_flag
    all_likes = importdata('LogLikelihood.txt');
    xhats = importdata('X.txt');
    all_params = [all_likes, xhats];
    [~,idx] = max(all_params(:,1));
    best_params = all_params(idx,:);
    max_likelihood = best_params(1,1)
    best_gamma = best_params(1,2)
    best_log_alpha = best_params(1,3)
    best_friction = best_params(1,4)
end

% save mcmc_run_1

%% Plot the results
figure; plot(all_likes)
title('Likelihood')

graph_correlations(xhats, 2, {'\gamma', 'log10(\alpha)', 'friction'}, 0, 0)

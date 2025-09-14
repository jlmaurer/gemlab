function [xhats, all_likes, all_dpreds, accept_rat] = mcmc(Niter, stepsize,...
    fun, x0, k, bounds,A, b, bcut, write_flag, varargin)
%MCMC: This function does MCMC sampling on fun, rejecting all samples that
%fall outside bounds, given an initial guess x0. An exit criteria may be
%provided which will terminate the function. 
%
% Inputs: 
%       Niter:      Number of simulations to perform
%       stepsize:   characteristic step distance
%       fun:        function to be evaluated
%       x0:         initial guess for x (x is mx1)
%       bounds:     a mx2 matrix specifying lower (col.1) and upper (col.2)
%                   bounds on x.
%       A:          matrix of conditions: enforced as Ax =<b
%       b:          vector of conditions: enforced as Ax =<b
%       varargin:   input variables for fun
%
% Outputs: 
%       results:    the results of sampling fun 

%% specify values
N= length(x0); 

%% specify default conditions
if isempty(x0)
    x0 = (bounds(:,2) - bounds(:,1))./2;
end

if isempty(A)
    A = eye(N); 
    b = inf([N, 1]); 
end

if isempty(bcut)
    bcut = 10; 
end

%% intialize loop
xprev = x0; 
[loglikeprev, dpred] = feval(fun, x0, bounds, varargin{:});
lb = bounds(:,1); 
ub = bounds(:,2);

%generate files to store results
if write_flag    
    %first create file
    fid = fopen('X.txt','w'); fclose(fid);  %store model parameters
    fid = fopen('LogLikelihood.txt','w'); fclose(fid);    %store log-likelihood

    %now open files to append
    fidX = fopen('X.txt','a');
    fidL = fopen('LogLikelihood.txt','a');
    
    xhats = []; all_dpreds = []; all_likes = []; accept_rates = [];
else
    xhats = zeros(N, Niter/k); 
    all_dpreds = zeros(length(dpred), Niter/k); 
    [accept_rats, all_likes] = deal(zeros(Niter/k, 1));
end

accept_count = 0; 

if length(stepsize)==1
    stepsize = stepsize*ones(size(x0)); 
end

%% Run MCMC loop
for loop=1:Niter

        x = xprev + stepsize.*(rand(size(xprev))-.5);

        mins = x<lb;
        maxs = x>ub;
        testbd = A*x; 
        test = testbd > b;
        
        % test if bounds are violated
        if any(mins) || any(maxs)
            accept =0; 
        
        % test secondary criteria
        elseif any(test)
                accept = 0; 
        else
            [loglike, dpred] = feval(fun, x, bounds, varargin{:});
            lograt = exp(loglike - loglikeprev); 
            
            if lograt>1
                accept=1;
            else
                r=rand;
                if r<lograt
                    accept=1;
                else
                    accept=0;
                end
            end
        end

        if accept==1
            xprev = x;
            loglikeprev = loglike; 
            accept_count = accept_count+1;
        else
            x = xprev;
            loglike = loglikeprev; 
        end

        %save every kth sample
        if mod(loop,k)==0
            if write_flag
                % **NOTE**: the first bcut samples are retained when
                % writing to file
                fprintf(fidX,'\n',' ');fprintf(fidX,'%6.8f\t',x');
                fprintf(fidL,'\n',' ');fprintf(fidL,'%6.8f\t',loglike);
            else
                xhats(:,loop/k) = x;
                all_likes(loop/k) = loglike; 
                all_dpreds(:,loop/k) = dpred; 
                accept_rats(loop/k) = accept_count/loop;
            end
        end   
        
end

%% Trim initial burn-in period
xhats(:,1:bcut) = []; 
all_likes(1:bcut) = []; 
all_dpreds(:,1:bcut) = []; 

accept_rat = accept_count / Niter;

disp(['Overall acceptance ratio was ', num2str(accept_rat)])

if write_flag
    fclose(fidX);
    fclose(fidL);
end
end

function [loglike, dpred] = likelihood_01(x, bounds, obs_dist, Nsim)

    gam = x(1);
    log10alpha = x(2);
    mu_f = x(3);
    
    alpha = 10.^log10alpha;
    
    sigma2_m = 25 * alpha;
    
    % check the bounds
    if any(x > bounds(:,2)) || any(x < bounds(:,1))
        loglike = -inf;
        dpred = [];
        return
    end
    
    % First compute the test_dist
    % For Nsim faults, calculate y/n and corresponding psis
    psi = repmat(180*rand(Nsim,1) - 90, 1, 1000); % adjust this to be between -90 - 90
    m = sigma2_m * randn(Nsim, 1000);
    y_or_no = compute_test_dist(m,psi,gam, mu_f);
    dpred = psi(logical(y_or_no));
    
    if length(dpred) < 10
        loglike = -inf;
        return
    end
        
    % Kolmogorov-Smirnov Metric
    [~,~, ksstat] = kstest2(obs_dist, dpred, 'Alpha', .05);
    loglike = -log(ksstat);
    
%     % CDF Pair Metric
%     [cdf1, cdf2] = getCDFpair(obs_dist, dpred);
%     loglike = -0.5*sum((cdf1 - cdf2).^2);
%     
%     disp(loglike);
%     histogram(dpred);
%     histogram(psi);

end

function [sampleCDF1, sampleCDF2, xout] = getCDFpair(x1, x2)
    binEdges    =  [-inf ; sort([x1;x2]) ; inf];

    binCounts1  =  histc (x1 , binEdges, 1);
    binCounts2  =  histc (x2 , binEdges, 1);

    sumCounts1  =  cumsum(binCounts1)./sum(binCounts1);
    sumCounts2  =  cumsum(binCounts2)./sum(binCounts2);

    sampleCDF1  =  sumCounts1(1:end-1);
    sampleCDF2  =  sumCounts2(1:end-1);
    
    xout = binEdges(2:end);
end

function [test_dist] = compute_test_dist(m, psi, gam, mu_f)
  
    top_part = @(m) (1 - m.^2) .* sind(2 * psi) - 2 * m .* cosd(2 * psi);
    bottom_part = @(m) ((1 + m.^2) ./ gam) - 2 * m .* sind(2*psi) - (1 - m.^2) .* cosd(2*psi);
    F = sign(psi) .* top_part(m) ./ bottom_part(m);
    
    test = F > mu_f;
    
    test_dist = logical(sum(test, 2));
end

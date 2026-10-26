fprintf('MATLAB version: %s\n', version);

simulinkLicense = license("test", "Simulink");
fprintf('Simulink license available: %d\n', simulinkLicense);

simFunction = which("sim");
fprintf('Simulink sim function: %s\n', simFunction);

if simulinkLicense ~= 1
    error('Simulink license is unavailable.');
end

if isempty(simFunction)
    error('Simulink sim function was not found.');
end

disp('MATLAB_SIMULINK_CHECK_PASSED');

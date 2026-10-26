modelFile = fullfile(fileparts(mfilename("fullpath")), "PediatricVitalGuard.slx");
load_system(modelFile);
model = "PediatricVitalGuard";

fprintf("Gain value: %s\n", get_param(model + "/Signal Pass Through", "Gain"));
fprintf("Input variable: %s\n", get_param(model + "/Synthetic Vital Signal", "VariableName"));
fprintf("Output variable: %s\n", get_param(model + "/Simulation Output", "VariableName"));

try
    fprintf("Output save format: %s\n", ...
        get_param(model + "/Simulation Output", "SaveFormat"));
catch
end

fprintf("Stop time: %s\n", get_param(model, "StopTime"));
close_system(model, 0);
disp("BLOCK_SETTINGS_CHECK_PASSED");

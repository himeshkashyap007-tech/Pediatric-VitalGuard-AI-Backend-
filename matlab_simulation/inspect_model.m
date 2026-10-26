modelFile = fullfile(pwd, "PediatricVitalGuard.slx");

if ~isfile(modelFile)
    modelFile = fullfile(fileparts(mfilename("fullpath")), "PediatricVitalGuard.slx");
end

fprintf("Model file: %s\n", modelFile);

if ~isfile(modelFile)
    error("MODEL_FILE_NOT_FOUND: %s", modelFile);
end

load_system(modelFile);
model = "PediatricVitalGuard";

fprintf("\n--- MODEL BLOCKS ---\n");
blocks = find_system(model, "SearchDepth", 1, "Type", "Block");

for k = 1:numel(blocks)
    fprintf("\nBlock: %s\n", blocks{k});
    fprintf("Type: %s\n", get_param(blocks{k}, "BlockType"));

    try
        fprintf("Variable name: %s\n", get_param(blocks{k}, "VariableName"));
    catch
    end
end

fprintf("\n--- MODEL CONNECTIONS ---\n");
lines = find_system(model, "FindAll", "on", "Type", "line");

for k = 1:numel(lines)
    try
        src = get_param(lines(k), "SrcBlock");
        dst = get_param(lines(k), "DstBlock");
        fprintf("Source block handle: %s\n", mat2str(src));
        fprintf("Destination block handles: %s\n", mat2str(dst));
    catch ME
        fprintf("Could not inspect line: %s\n", ME.message);
    end
end

close_system(model, 0);
disp("MODEL_INSPECTION_PASSED");

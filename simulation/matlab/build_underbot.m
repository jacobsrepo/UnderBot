function report = build_underbot()
% Rebuild the fixed-base R09 import and run a short passive smoke simulation.
here = fileparts(mfilename('fullpath'));
root = fileparts(fileparts(here));
package = fullfile(root,'models','r09','underbot_description');
source = fullfile(package,'urdf','underbot.portable.urdf');
out = fullfile(here,'generated');
if ~isfolder(out), mkdir(out); end
previous = pwd;
restore = onCleanup(@() cd(previous));
cd(out);
addpath(fullfile(package,'meshes'));
Simulink.fileGenControl('set','CacheFolder',fullfile(out,'cache'), ...
    'CodeGenFolder',fullfile(out,'codegen'),'createDir',true);
fprintf('STAGE: audit source\n');
doc = xmlread(source);
links = doc.getElementsByTagName('link');
joints = doc.getElementsByTagName('joint');
report = struct('matlab',version,'source','models/r09/underbot_description/urdf/underbot.portable.urdf', ...
    'base','fixed to world','links',links.getLength,'joints',joints.getLength, ...
    'mass_kg',0,'inertia_checks_passed',true,'joint_inventory',[]);
inventory = repmat(struct('name','','type','','mimic','','lower',[],'upper',[]),joints.getLength,1);
for k = 0:links.getLength-1
    link = links.item(k);
    inertials = link.getElementsByTagName('inertial');
    if inertials.getLength == 0, continue; end
    inertial = inertials.item(0);
    mass = str2double(inertial.getElementsByTagName('mass').item(0).getAttribute('value'));
    assert(isfinite(mass) && mass >= 0,'Invalid mass');
    report.mass_kg = report.mass_kg + mass;
    tensor = inertial.getElementsByTagName('inertia').item(0);
    a = @(name) str2double(tensor.getAttribute(name));
    I = [a('ixx') a('ixy') a('ixz'); a('ixy') a('iyy') a('iyz'); a('ixz') a('iyz') a('izz')];
    if mass == 0
        name = char(link.getAttribute('name'));
        fixedFrame = false;
        for j = 0:joints.getLength-1
            candidate = joints.item(j);
            child = candidate.getElementsByTagName('child').item(0);
            if strcmp(char(child.getAttribute('link')),name)
                fixedFrame = strcmp(char(candidate.getAttribute('type')),'fixed');
            end
        end
        assert(fixedFrame && all(I(:)==0),'Only fixed reference frames may be massless');
        continue
    end
    principal = sort(eig(I));
    assert(all(isfinite(principal)) && all(principal > 0),'Invalid inertia');
    assert(principal(3) <= sum(principal(1:2)) + 1e-10,'Nonphysical principal inertia');
end
for k = 0:joints.getLength-1
    joint = joints.item(k);
    entry = struct('name',char(joint.getAttribute('name')), ...
        'type',char(joint.getAttribute('type')),'mimic','','lower',[],'upper',[]);
    mimic = joint.getElementsByTagName('mimic');
    if mimic.getLength > 0, entry.mimic = char(mimic.item(0).getAttribute('joint')); end
    limit = joint.getElementsByTagName('limit');
    if limit.getLength > 0 && strcmp(entry.type,'revolute')
        entry.lower = str2double(limit.item(0).getAttribute('lower'));
        entry.upper = str2double(limit.item(0).getAttribute('upper'));
        assert(entry.lower <= 0 && entry.upper >= 0,'Zero pose outside joint limits');
    end
    inventory(k+1) = entry; %#ok<AGROW>
end
report.joint_inventory = inventory;
assert(report.links == 23 && report.joints == 22,'Unexpected R09 topology');
assert(abs(report.mass_kg-19.6010078) < 1e-6,'Unexpected R09 mass');
% Use basenames in a derived import file, resolving geometry through MATLAB's path.
% The original URDF and all geometry remain untouched.
meshes = doc.getElementsByTagName('mesh');
for k = 0:meshes.getLength-1
    mesh = meshes.item(k);
    [~,name,ext] = fileparts(char(mesh.getAttribute('filename')));
    assert(isfile(fullfile(package,'meshes',[name ext])),'Missing mesh: %s',name);
    mesh.setAttribute('filename',[name ext]);
end
derived = fullfile(out,'underbot_r09_import.urdf');
xmlwrite(derived,doc);
model = 'underbot_r09_fixed_base';
assert(~bdIsLoaded(model),'Close the existing generated model before rebuilding.');
fprintf('STAGE: smimport\n');
smimport(derived,'ModelName',model);
set_param(model,'StopTime','0.05','Solver','ode15s','MaxStep','0.005');
% Capture every block parameter so importer behavior can be reviewed explicitly.
blocks = find_system(model,'Type','Block');
details = struct([]);
for k = 1:numel(blocks)
    params = get_param(blocks{k},'DialogParameters');
    values = struct;
    if isstruct(params)
        for name = string(fieldnames(params))'
            values.(name) = get_param(blocks{k},name);
        end
    end
    details(k).path = blocks{k}; %#ok<AGROW>
    details(k).reference = get_param(blocks{k},'ReferenceBlock');
    details(k).parameters = values;
end
write_json(fullfile(out,'imported_blocks.json'),details);
save_system(model,fullfile(out,[model '.slx']));
fprintf('STAGE: model update\n');
set_param(model,'SimulationCommand','update');
report.update_passed = true;
fprintf('STAGE: passive simulation 0.05 s\n');
result = sim(model,'ReturnWorkspaceOutputs','on');
assert(isempty(result.ErrorMessage),'Simulation reported an error');
report.simulation_end_s = result.tout(end);
assert(abs(report.simulation_end_s-0.05) < 1e-9,'Simulation stopped early');
report.simulation_passed = true;
report.scope = 'Fixed-base passive gravity smoke test; no ground contact, motors or control. Hardware properties remain estimates.';
write_json(fullfile(out,'verification.json'),report);
save_system(model);
fprintf('UNDERBOT_IMPORT_AND_SIMULATION_PASSED\n');
close_system(model,0);
end

function write_json(path,value)
file = fopen(path,'w');
assert(file ~= -1,'Cannot write %s',path);
cleanup = onCleanup(@() fclose(file));
fprintf(file,'%s\n',jsonencode(value,PrettyPrint=true));
end

function open_underbot()
% Open the generated R09 model with portable mesh resolution.
here = fileparts(mfilename('fullpath'));
root = fileparts(fileparts(here));
addpath(fullfile(root,'models','r09','underbot_description','meshes'));
Simulink.fileGenControl('set','CacheFolder',fullfile(here,'generated','cache'), ...
    'CodeGenFolder',fullfile(here,'generated','codegen'),'createDir',true);
model = fullfile(here,'generated','underbot_r09_fixed_base.slx');
assert(isfile(model),'Run build_underbot first.');
open_system(model);
end

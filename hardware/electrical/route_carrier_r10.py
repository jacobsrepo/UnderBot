"""Reproducible routed review revision; release holds are documented separately."""
from pathlib import Path
import shutil,json
import pcbnew as p
import build_schematic_r05 as k
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'Carrier-r10';OUT.mkdir(exist_ok=True)
for name in ['UnderBot.kicad_sch','Carrier.kicad_sch','UnderBot.kicad_pro','placement.json','module-selection.csv','budget-r09.xlsx']:
    shutil.copy2(ROOT/'Carrier-r09'/name,OUT/name)
for name in ['UnderBot.kicad_sch','Carrier.kicad_sch']:
    path=OUT/name;s=path.read_text(encoding='utf-8').replace('r09','r10').replace('UNROUTED','ROUTED REVIEW - NOT FOR FABRICATION');path.write_text(s,encoding='utf-8')
path=OUT/'Carrier.kicad_sch';doc=path.read_text(encoding='utf-8')
endpoint=k.Sheet('Carrier','');endpoint.counter=1000
lid=k.module_library('Pi_USB_C_Input',['USB_C_PD'],[])
endpoint.add(lid,'A3','Raspberry Pi 5 USB-C input',375.92,76.2,onboard=False)
endpoint.net('A3','USB_C_PD','USB_C_TO_PI')
libend=doc.index('(lib_symbols')+len('(lib_symbols')
doc=doc[:libend]+endpoint.libs[lid]+doc[libend:]
doc=doc.rstrip()[:-1]+''.join(endpoint.items)+')'
for ref in ['A1','A2','A3']:
    doc=doc.replace('(on_board yes) (dnp no) (uuid '+k.ident('Carrier'+ref), '(on_board no) (dnp no) (uuid '+k.ident('Carrier'+ref))
doc=doc.replace('0.9 CARRIER','1.0 ROUTED REVIEW').replace('2026-10-02','2026-10-03')
path.write_text(doc,encoding='utf-8')
names=['Aux_Pololu_D24V50F5','Pi_EP0225','Kinect_DDR60G12','Pi_USB_C_Input']
raws=[k.extract(doc,'UnderBot_Modules:'+n).replace('(symbol "UnderBot_Modules:'+n+'"','(symbol "'+n+'"',1) for n in names]
(OUT/'UnderBot_Modules.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor") '+''.join(raws)+')',encoding='utf-8')
(OUT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "UnderBot_Modules") (type "KiCad") (uri "${KIPRJMOD}/UnderBot_Modules.kicad_sym") (options "") (descr "Carrier interfaces")))')
b=p.LoadBoard(str(ROOT/'Carrier-r09/UnderBot.kicad_pcb'))
def xy(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def route(net,points,width=3,layer=p.F_Cu):
    for a,c in zip(points,points[1:]):
        t=p.PCB_TRACK(b);t.SetStart(xy(*a));t.SetEnd(xy(*c));t.SetWidth(p.FromMM(width));t.SetLayer(layer);t.SetNetCode(b.GetNetcodeFromNetname(net));b.Add(t)
# Save the actual custom footprint in a project library, with no board net data.
lib=OUT/'UnderBotCarrier.pretty';lib.mkdir(exist_ok=True)
plugin=p.PCB_IO_MGR.FindPlugin(p.PCB_IO_MGR.KICAD_SEXP)
for f in b.GetFootprints():
    f.SetPath(p.KIID_PATH('/'+k.ROOT+'/'+k.ident('sheet/Carrier')+'/'+k.ident('Carrier'+f.GetReference())))
    if f.GetReference()=='U3':
        f.Reference().SetPosition(xy(150,169))
        plugin.FootprintSave(str(lib),f)
for a in b.GetDrawings():
    if isinstance(a,p.PCB_TEXT):a.SetText(a.GetText().replace('r09','r10').replace('UNROUTED / REVIEW ONLY','ROUTED / NOT FOR FAB'))
# Wide distribution trunks; these dimensions are not a certified current rating.
route('VIN',[(60,66),(57,69),(57,200),(60,200)],4)
for y in [95,135]:route('VIN',[(57,y),(62,y)],3)
for f in b.GetFootprints():
    if f.GetReference().startswith('F'):
        for number in ['1','2']:
            pads=[z for z in f.Pads() if z.GetNumber()==number]
            route(pads[0].GetNetname(),[(p.ToMM(z.GetPosition().x),p.ToMM(z.GetPosition().y)) for z in pads],3)
route('PI_IN',[(71.92,98.4),(78,104.48),(78,139),(84,145),(160,145)])
route('KINECT_IN',[(71.92,138.4),(82,148.48),(172,148.48),(172,177),(180,185),(190,185)],3,p.B_Cu)
route('ACT',[(65.08,200),(73,192.08),(73,185),(100,185),(110,175),(110,173.4)],4)
route('ACT',[(85,185),(85,195)],3)
route('ARM_IN',[(94.92,198.4),(94.92,204.92),(105,215)])
route('AUX_IN',[(119.92,173.4),(130,173.4),(140,183.4),(150.255,183.4)],3)
route('AUX_IN',[(150.255,183.4),(150.255,191.05)],1.2)
route('AUX_5V',[(157.875,191.05),(157.875,198)],1.2)
route('AUX_5V',[(157.875,198),(150,205.875),(150,210),(155,210)],3)
route('DEPTH_12',[(222,62),(218,66),(218,170),(225,177),(225,200),(230,200)],3)
# Ground on both layers; direct pad connections avoid undersized thermal spokes.
for layer in [p.F_Cu,p.B_Cu]:
    z=p.ZONE(b);z.SetLayer(layer);z.SetNetCode(b.GetNetcodeFromNetname('GND'));z.SetLocalClearance(p.FromMM(.5));z.SetPadConnection(p.ZONE_CONNECTION_FULL);z.SetMinThickness(p.FromMM(.25))
    poly=z.Outline();poly.NewOutline()
    for x,y in [(51,51),(249,51),(249,229),(51,229)]:poly.Append(int(p.FromMM(x)),int(p.FromMM(y)))
    b.Add(z)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones())
# Keep PCB identities, values and hierarchical net names aligned with the schematic.
tree=k.parse(doc)
values={next(v[2] for v in k.children(s,'property') if v[1]=='Reference'):next(v[2] for v in k.children(s,'property') if v[1]=='Value') for s in k.children(tree,'symbol')}
placements={a['ref']:a for a in json.loads((OUT/'placement.json').read_text())}
for f in b.GetFootprints():
    ref=f.GetReference();f.SetValue(values[ref]);libname,fpname=placements[ref]['footprint'].split(':');f.SetFPID(p.LIB_ID(libname,fpname))
    f.SetAttributes(f.GetAttributes() & ~p.FP_EXCLUDE_FROM_BOM)
    field=p.PCB_FIELD(f,p.FIELD_T_USER,'Assembly');field.SetText('PCB/harness TBD');field.SetVisible(False);f.Add(field)
for net in list(b.GetNetsByNetcode().values()):
    if net.GetNetname():net.SetNetname('/Converter carrier circuit r10/'+net.GetNetname())
nc=p.NETINFO_ITEM(b,'unconnected-(U3-EN-Pad1)');b.Add(nc)
for f in b.GetFootprints():
    if f.GetReference()=='U3':
        for pad in f.Pads():
            if pad.GetNumber()=='1':pad.SetNet(nc)
p.SaveBoard(str(OUT/'UnderBot.kicad_pcb'),b)
(OUT/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "UnderBotCarrier") (type "KiCad") (uri "${KIPRJMOD}/UnderBotCarrier.pretty") (options "") (descr "Pololu daughterboard - physical fit check required")))')
# Explicit project tables avoid slow global nested-table resolution in this installation.
for filename,kind,entries,folder,suffix,var in [
    ('fp-lib-table','KiCad',['Fuse','MountingHole','TerminalBlock_Phoenix'],'footprints','.pretty','KICAD10_FOOTPRINT_DIR'),
    ('sym-lib-table','KiCad',['Device','Mechanical','Connector_Generic'],'symbols','.kicad_sym','KICAD10_SYMBOL_DIR')]:
    path=OUT/filename;table=path.read_text().rstrip()[:-1]
    for name in entries:table+=f'(lib (name "{name}") (type "{kind}") (uri "${{{var}}}/{name}{suffix}") (options "") (descr "KiCad standard library"))'
    path.write_text(table+')')
(OUT/'routing-summary.json').write_text(json.dumps({'tracks':len(list(b.GetTracks())),'zones':len(list(b.Zones())),'widths_mm':[1.2,3,4],'release':'HOLD: fuse coordination, physical fit, thermal and external protection validation'},indent=2))
print('Saved',OUT)

# This is the file that is executed by the bokeh server.
# """This plots the exoplanet population to create a plot of selectable planets
# in the exoplanet population, using the interactive Bokeh server.
#
#
# Jens Hoeijmakers, 05-05-2020
#
# This used the IMDB explorer example (https://github.com/bokeh/bokeh/blob/master/examples/app/movies/main.py),
# and a Gist by Brett Morris (github bmorris3) as a starting points."""
import numpy as np
# import matplotlib.pyplot as plt
import astropy.units as u
from astroquery.nasa_exoplanet_archive import NasaExoplanetArchive
import copy
import sys
import numpy as np
from bokeh.io import curdoc, show, reset_output
from bokeh.layouts import column, layout, row
from bokeh.models import ColumnDataSource, Div, Select, Slider, TextInput,RangeSlider,RadioGroup,CheckboxGroup
from bokeh.models.formatters import FuncTickFormatter
from bokeh.models.callbacks import CustomJS
from bokeh.plotting import figure
from os.path import dirname, join
from datetime import date
import math


def prep_table():
    """This is a wrapper for reading and augmenting the Exoplanet data table to be suitable for interaction with bokeh.
    It computes the equilibrium temperature, converts masses and radii."""

#TO DO: SOME PLANETS FALL OUT BECAUSE THEY DONT HAVE A STELLAR EFFECTIVE TEMPERATURE AND/OR STELLAR RADIUS.
#HOWEVER THESE CAN BE APPROXIMATED FROM THE SPECTRAL TYPE. FOR EACH MISSING VALUE, I NEED TO LOOK UP WHAT A STAR WITH
#THAT SPECTRAL TYPE TYPICALLY HAS FOR VALUES OF R_S AND T_EFF, AND REPLACE THOSE.
    table = NasaExoplanetArchive.get_confirmed_planets_table(all_columns=True)#This is an astropy table.
    transiting = table[(table['pl_tranflag'].data).astype(bool)]#Select only the transiting ones, and put them in a new table.
    # transiting['pl_rade']=transiting['pl_radj'].to('earthRad')

    equilibrium_temperature = (transiting['st_teff'] * np.sqrt(transiting['st_rad'] / 2 / transiting['pl_orbsmax'])).decompose()#Compute T_eq.
    g = transiting['gaia_gmag'].quantity#Short-hand for the Gaia magnitude.

    transiting['teq'] = equilibrium_temperature

    transiting['colour'] = 'gray'#These set the appearance of the entries in the plot.
    transiting['selcolour'] = 'orange'
    transiting['alpha'] = 0.5

    transiting['planetradius'] = transiting['pl_radj']*1.0
    transiting['planetmass'] = transiting['pl_massj']*1.0
    return(transiting)





DF = prep_table()
print(DF.colnames)
# sys.exit()


# Create Column Data Source that will be used by the plot.
# We create 2 tables. One that contains *all* planets; one that contains only the selected planets.
datatable = ColumnDataSource(data=dict(x=[],y=[],P=[],Rp=[], Mp=[], T_eff=[], Name=[], Year=[], T_eq=[], Gmag=[],Jmag=[],color=[],alpha=[],rho=[],ecc=[],FeH=[]))
seltable = ColumnDataSource(data=dict(x=[],y=[],P=[],Rp=[], Mp=[], T_eff=[], Name=[], Year=[], T_eq=[], Gmag=[],Jmag=[],selcolor=[],alpha=[],rho=[],ecc=[],FeH=[]))

axis_map = {
    "Planet mass": "planetmass",
    "Planet radius": "planetradius",
    "Orbital period": "pl_orbper",
    "Eccentricity":"pl_orbeccen",
    "Equilibrium temperature": "teq",
    "Stellar Effective Temperature": "st_teff",
    "Density": "pl_dens",
    "Gaia magnitude":"gaia_gmag",
    "2MASS J magnitude":"st_j",
    "Metallicity [Fe/H]":"st_metfe",
    "Year of discovery": "pl_disc",
}
unit_map = {
    "Planet mass": "(Mj)",
    "Planet radius": "(Rj)",
    "Orbital period": "(d)",
    "Eccentricity":"",
    "Equilibrium temperature": "(K)",
    "Stellar Effective Temperature": "(K)",
    "Density": '(g/cm3)',
    "Gaia magnitude":"",
    "2MASS J magnitude":"",
    "Metallicity [Fe/H]":"(dex)",
    "Year of discovery": "",
}



TOOLTIPS=[("Name","@Name"),("Mass", "@Mp"),("Radius", "@Rp"),("P", "@P d"),("Gmag/Jmag", "@Gmag/@Jmag"),("Teq", "@T_eq K")]
#Note that the format of the tooltip can be completely customised using HTML code; see: https://docs.bokeh.org/en/latest/docs/user_guide/tools.html
#E.g.:
# TOOLTIPS = """
#     <div>
#         <div>
#             <img
#                 src="@imgs" height="42" alt="@imgs" width="42"
#                 style="float: left; margin: 0px 15px 15px 0px;"
#                 border="2"
#             ></img>
#         </div>
#         <div>
#             <span style="font-size: 17px; font-weight: bold;">@desc</span>
#             <span style="font-size: 15px; color: #966;">[$index]</span>
#         </div>
#         <div>
#             <span>@fonts{safe}</span>
#         </div>
#         <div>
#             <span style="font-size: 15px;">Location</span>
#             <span style="font-size: 10px; color: #696;">($x, $y)</span>
#         </div>
#     </div>
# """


#Determine slider limits
lim_mass = (0,math.ceil(np.nanmax(DF['planetmass'])))
lim_year = (np.nanmin(DF["pl_disc"]),int(date.today().year))#Limit year between first discovery and now.
lim_mag  = (math.floor(np.nanmin(DF["gaia_gmag"])),math.ceil(np.max(DF["gaia_gmag"])))
lim_jmag = (math.floor(np.nanmin(DF["st_j"])),math.ceil(np.max(DF["st_j"])))
# lim_teq  = (0,math.ceil(np.nanmax(DF['teq'].to('K').value)/1000.0)*1000.0)#Will need to deal with infinites here.
lim_teq = (0,5000)
lim_rad  = (0,math.ceil(np.nanmax(DF['planetradius'].to('jupiterRad').value)))
lim_teff = (0,math.ceil(np.nanmax(DF['st_teff'].to('K').value)/1000.0)*1000.0)
lim_per  = (0,math.ceil(np.nanmax(DF['pl_orbper'].to('d').value)/1000.0)*1000.0)
lim_ecc = (0,1)



#Here comes something tricky. Masses and radii are quantities that vary relevantly over orders of magnitude, from 0 to 30Mj. There are 'special' values
#like 1Mj, 1Re, 1.6Re, etc. These are hard to capture in a functional form with some logarithm.
#So I hardcoded them into string arrays; in the form of a JScript function that is passed to FuncTickFormatter that is passed to the format keyword that is passed to the RangeSlider.
#...
#The slider is now sliding through list-indices (step = 1, min=0, max=len(list)).
#See the RangeSlider definitions below.
#Now, why is it a problem that this is hardcoded?
#Because there are variables that depend on the values in this list, for example the start and end of the rangeslider (i.e. the start and end index of this list, 0 and len(list)).
#But more importantly, these values need to be queried later when the output values of the sliders are used.
#This means that a python version of this ticker definition needs to exist, with numbers in it, with a unit of mass or kg, such that the planet database can be queried.
#The easy way to do this is to simply copy-paste the below array var v=[...] arrays and make them python.
#But that would be dangerous - hardcoding something like this is already bad enough.
mass_ticker="""
    var v=['0 Me','1 Me','2 Me','5 Me','10 Me','20 Me (0.06 Mj)','0.1 Mj (32 Me)','0.2 Mj','0.5 Mj','0.8 Mj','1 Mj','1.5 Mj','2 Mj','3 Mj','5 Mj','8 Mj','10 Mj','13 Mj','20 Mj','30 Mj','50 Mj'];
    return v[tick]
    """
radius_ticker="""
    var v=['0 Re','0.5 Re','1 Re','1.6 Re','2 Re','3 Re (0.27 Rj)','4 Re (0.36 Rj)','5 Re (0.45 Rj)','0.5 Rj','0.8 Rj','1 Rj','1.2 Rj','1.5 Rj','1.8 Rj','2 Rj','2.5 Rj','3 Rj','5 Rj'];
    return v[tick]
    """
#So why not write a python script that extracts and converts these?
#Why not?
#Here goes. First split out (on the line breaks) the line that contains the definition var v=, replace the
mass_ticks=mass_ticker.split('\n')[1].replace('    var v=[','').replace('];','').replace("'",'').split(',')#This is a list of strings. Well done, Python.
radius_ticks=radius_ticker.split('\n')[1].replace('    var v=[','').replace('];','').replace("'",'').split(',')#and the same for radius....
mass_tick_values=[]
radius_tick_values=[]
for i in mass_ticks:
    value=i.split(' ')[0]#The value is always the thing that is a number before the first space.
    if i.split(' ')[1] == 'Me':
        unit=u.earthMass
    elif i.split(' ')[1] == 'Mj':
        unit=u.jupiterMass
    else:
        print('ERROR: COULD NOT RESOLVE JScript string of mass ticks. Tried to resolve the following:')
        print(i.split(' ')[1])
    mass_tick_values.append(value*unit)
for i in radius_ticks:
    value=i.split(' ')[0]#The value is always the thing that is a number before the first space.
    if i.split(' ')[1] == 'Re':
        unit=u.earthRad
    elif i.split(' ')[1] == 'Rj':
        unit=u.jupiterRad
    else:
        print('ERROR: COULD NOT RESOLVE JScript string of radius ticks. Tried to resolve the following:')
        print(i.split(' ')[1])
    radius_tick_values.append(value*unit)
#WHAM!
#So.....
#IF  YOU  EVER  WANT  TO  CHANGE  THE VALUES  OR  NUMBER  OF TICKS  IN  THE  MASS  OR  RADIUS  SLIDERS!
#ONLY TOUCH THE JScript ARRAYS STARTING WITH var=[...], FILL THEM IN THERE WITH EITHER Me or Mj FOR EARTH OR JUPITER MASSES
#AND Re OR Rj FOR EARTH OR JUPITER RADII. THE ABOVE RESOLVER WILL DO THE REST.
#I love you, Python.
#But do not touch the number of spaces before the var= thing or it will break. Do not touch any of that syntax, in fact.
#I reproduce here how the variables should look in a working state, for safekeeping:
#mass_ticker="""
#    var v=['0 Me','1 Me','2 Me','5 Me','10 Me','20 Me (0.06 Mj)','0.1 Mj (32 Me)','0.2 Mj','0.5 Mj','0.8 Mj','1 Mj','1.5 Mj','2 Mj','3 Mj','5 Mj','8 Mj','10 Mj','13 Mj','20 Mj','30 Mj','50 Mj'];
#    return v[tick]
#    """
#radius_ticker="""
#    var v=['0 Re','0.5 Re','1 Re','1.6 Re','2 Re','3 Re (0.27 Rj)','4 Re (0.36 Rj)','5 Re (0.45 Rj)','0.5 Rj','0.8 Rj','1 Rj','1.2 Rj','1.5 Rj','1.8 Rj','2 Rj','2.5 Rj','3 Rj','5 Rj'];
#    return v[tick]
#    """




# Create sliders and other controls
# mass = RangeSlider(start=lim_mass[0], end=lim_mass[1], value=lim_mass,value_throttled=lim_mass, step=.1, title=list(axis_map.keys())[0])
mass = RangeSlider(start=0, end=20, value=(0,20),value_throttled=(0,20), step=1, title=list(axis_map.keys())[0],format=FuncTickFormatter(code=mass_ticker))
# rad  = RangeSlider(start=lim_rad[0], end=lim_rad[1], value=lim_rad,value_throttled=lim_rad, step=.1, title=list(axis_map.keys())[1])
rad  = RangeSlider(start=0, end=16, value=(0,16),value_throttled=(0,16), step=1, title=list(axis_map.keys())[1],format=FuncTickFormatter(code=radius_ticker))
# per  = RangeSlider(start=lim_per[0], end=lim_per[1], value=lim_per, step=.1, title=list(axis_map.keys())[2])
per  = RangeSlider(start=-1.5,end=4, value=[-1.5,4],value_throttled=[-1.5,4], step=.01, title=list(axis_map.keys())[2],format=FuncTickFormatter(code="return (10**tick).toFixed(2)"))
ecc  = RangeSlider(start=0,end=1,value=lim_ecc,value_throttled=lim_ecc,step=0.05,title=list(axis_map.keys())[3])
teq  = RangeSlider(start=lim_teq[0], end=lim_teq[1], value=lim_teq,value_throttled=lim_teq, step=100, title=list(axis_map.keys())[4])
teff = RangeSlider(start=lim_teff[0], end=lim_teff[1], value=lim_teff,value_throttled=lim_teff, step=1000, title=list(axis_map.keys())[5])
mag  = RangeSlider(start=lim_mag[0], end=lim_mag[1], value=lim_mag,value_throttled=lim_mag, step=.1, title=list(axis_map.keys())[7])
Jmag = RangeSlider(start=lim_jmag[0], end=lim_jmag[1], value=lim_jmag,value_throttled=lim_jmag, step=.1, title=list(axis_map.keys())[8])
# year = RangeSlider(start=lim_year[0], end=lim_year[1], value=lim_year,value_throttled=lim_year, step=1, title=list(axis_map.keys())[8])
units = RadioGroup(labels=["Jupiter","Earth"], active=0)
axis_log = CheckboxGroup(labels=["log(x)", "log(y)"], active=[0])
# Type  =  Select(title="Type", value="All",options=['All','TOI','Transiting','Non-transiting (RV)','Directly imaged'])
x_axis = Select(title="X Axis", options=sorted(axis_map.keys()), value=list(axis_map.keys())[2])
y_axis = Select(title="Y Axis", options=sorted(axis_map.keys()), value=list(axis_map.keys())[1])





#Create 4 figures with different combinations of xlog and ylog.
p1 = figure(plot_height=200, plot_width=200, title="", toolbar_location="right",toolbar_sticky=False,sizing_mode="scale_height",tooltips=TOOLTIPS,x_axis_type="linear",y_axis_type='linear',visible=False)
p2 = figure(plot_height=200, plot_width=200, title="", toolbar_location="right",toolbar_sticky=False,sizing_mode="scale_height",tooltips=TOOLTIPS,x_axis_type="log",y_axis_type='linear',visible=False)
p3 = figure(plot_height=200, plot_width=200, title="", toolbar_location="right",toolbar_sticky=False,sizing_mode="scale_height",tooltips=TOOLTIPS,x_axis_type="linear",y_axis_type='log',visible=False)
p4 = figure(plot_height=200, plot_width=200, title="", toolbar_location="right",toolbar_sticky=False,sizing_mode="scale_height",tooltips=TOOLTIPS,x_axis_type="log",y_axis_type='log',visible=False)
p1.circle(x="x", y="y", source=datatable, size=7, color="color", line_color=None, fill_alpha="alpha")
p2.circle(x="x", y="y", source=datatable, size=7, color="color", line_color=None, fill_alpha="alpha")
p3.circle(x="x", y="y", source=datatable, size=7, color="color", line_color=None, fill_alpha="alpha")
p4.circle(x="x", y="y", source=datatable, size=7, color="color", line_color=None, fill_alpha="alpha")
p1.circle(x="x", y="y", source=seltable, size=7, color="selcolor", line_color=None, fill_alpha="alpha")
p2.circle(x="x", y="y", source=seltable, size=7, color="selcolor", line_color=None, fill_alpha="alpha")
p3.circle(x="x", y="y", source=seltable, size=7, color="selcolor", line_color=None, fill_alpha="alpha")
p4.circle(x="x", y="y", source=seltable, size=7, color="selcolor", line_color=None, fill_alpha="alpha")
#All of them are set to invisible.




def update():
    """This updates the axis labels and circles after changing the axes or selection sliders."""
    for p in [p1,p2,p3,p4]:
        p.xaxis.axis_label = x_axis.value+' '+unit_map[x_axis.value]
        p.yaxis.axis_label = y_axis.value+' '+unit_map[y_axis.value]
    x_name = axis_map[x_axis.value]
    y_name = axis_map[y_axis.value]
    #This is where the actual conversion between the exoplanet input table and the dataframe read by Bokeh is done.
    datatable.data = dict(x=DF[x_name],y=DF[y_name],P=DF["pl_orbper"],Mp=DF["planetmass"],Rp=DF["planetradius"],T_eq=np.round(DF["teq"],0),Gmag=np.round(DF["gaia_gmag"],1),Jmag=np.round(DF["st_j"],1),color=DF["colour"],alpha=DF["alpha"],Name=DF["pl_name"],rho=DF['pl_dens'],ecc=DF['pl_orbeccen'],FeH=DF["st_metfe"])#All this additional info is needed ONLY for the tooltip. Just sayin.

    #This fixes the horribly looking superscripts native to Bokeh, kindly adopted from jdbocarsly on issue 6031; https://github.com/bokeh/bokeh/issues/6031
    fix_substring_JS = """
        var str = Math.log10(tick).toString(); //get exponent
        var newStr = "";
        for (var i=0; i<str.length;i++)
        {
            var code = str.charCodeAt(i);
            switch(code) {
                case 45: // "-"
                    newStr += "⁻";
                    break;
                case 49: // "1"
                    newStr +="¹";
                    break;
                case 50: // "2"
                    newStr +="²";
                    break;
                case 51: // "3"
                    newStr +="³"
                    break;
                default: // all digit superscripts except 1, 2, and 3 can be generated by adding 8256
                    newStr += String.fromCharCode(code+8256)
            }
        }
        return 10+newStr;
    """
    normal_logstring_JS="return tick"
    if x_name == 'planetmass' or x_name == 'planetradius' or x_name == 'pl_orbper':
        p4.xaxis[0].formatter = FuncTickFormatter(code=fix_substring_JS)
        p2.xaxis[0].formatter = FuncTickFormatter(code=fix_substring_JS)
    else:
        p4.xaxis[0].formatter = FuncTickFormatter(code=normal_logstring_JS)
        p2.xaxis[0].formatter = FuncTickFormatter(code=normal_logstring_JS)
    if y_name == 'planetmass' or y_name == 'planetradius' or y_name == 'pl_orbper':
        p3.yaxis[0].formatter = FuncTickFormatter(code=fix_substring_JS)
        p4.yaxis[0].formatter = FuncTickFormatter(code=fix_substring_JS)
    else:
        p3.yaxis[0].formatter = FuncTickFormatter(code=normal_logstring_JS)
        p4.yaxis[0].formatter = FuncTickFormatter(code=normal_logstring_JS)
    #Wow. And it all still runs smoothly.
    update_selection()

def change_logscale():
    """This determines the value of the x-log, y-log buttons, and
    changes the scale of the x and y axes accordingly.

    Well, not 'change', but rather make visible the plot with the correct
    combination of xlog and ylog. A bit cumbersome but so be it."""
    for p in [p1,p2,p3,p4]:
        p.visible=False#Set all figures to invisible.
    #And then make only one visible again:
    # print(axis_log.active)
    if len(axis_log.active) == 0:
        # print('Making p1 active')
        p1.visible=True
    elif len(axis_log.active) ==2:
        # print('Making p4 active')
        p4.visible=True
    elif 0 in axis_log.active:
        # print('Making p2 active')
        p2.visible=True
    else:
        # print('Making p3 active')
        p3.visible=True

def change_units():
    """This switches the units of radius and mass between Jupiter (default) and Earth via the radio button."""
    if units.labels[units.active] == 'Jupiter':
        DF['planetradius'] = DF['pl_radj']*1.0
        DF['planetmass'] = DF['pl_massj']*1.0
        unit_map["Planet mass"] = "(Mj)"
        unit_map["Planet radius"] = "(Rj)"
    elif units.labels[units.active] == 'Earth':
        DF['planetradius'] = DF['pl_rade']*1.0
        DF['planetmass'] = DF['pl_masse']*1.0
        unit_map["Planet mass"] = "(Me)"
        unit_map["Planet radius"] = "(Re)"
    else:
        print("ERROR: UNITS IS SET TO %s BUT THIS ISNT HANDLED."%units.labels[units.active])
    update()
def update_selection():
    x_name = axis_map[x_axis.value]
    y_name = axis_map[y_axis.value]
    # mass = RangeSlider(start=lim_mass[0], end=lim_mass[1], value=lim_mass,value_throttled=lim_mass, step=.1, title=list(axis_map.keys())[0])
    # rad  = RangeSlider(start=lim_rad[0], end=lim_rad[1], value=lim_rad,value_throttled=lim_rad, step=.1, title=list(axis_map.keys())[1])
    # # per  = RangeSlider(start=lim_per[0], end=lim_per[1], value=lim_per, step=.1, title=list(axis_map.keys())[2])
    # per  = RangeSlider(start=-1.5,end=4, value=[-1.5,4],value_throttled=[-1.5,4], step=.01, title=list(axis_map.keys())[2],format=FuncTickFormatter(code="return (10**tick).toFixed(2)"))
    # teq  = RangeSlider(start=lim_teq[0], end=lim_teq[1], value=lim_teq,value_throttled=lim_teq, step=100, title=list(axis_map.keys())[3])
    # teff = RangeSlider(start=lim_teff[0], end=lim_teff[1], value=lim_teff,value_throttled=lim_teff, step=1000, title=list(axis_map.keys())[4])
    # mag  = RangeSlider(start=lim_mag[0], end=lim_mag[1], value=lim_mag,value_throttled=lim_mag, step=.1, title=list(axis_map.keys())[5])
    # year = RangeSlider(start=lim_year[0], end=lim_year[1], value=lim_year,value_throttled=lim_year, step=1, title=list(axis_map.keys())[6])

    #Ok some weird unit things here.
    #DF["pl_massj"] gives the mass without astropy unit; so just floats, in jupiter masses.
    #DF["pl_radj"] gives the radius with an astropy unit of jupiter radii.
    #So for the mass I dont pick the value of the column, but for radius I do.
    #Secondly, unit.to('jupiterMass') returns a FLOAT, not an astropy unit.
    mass_min = mass_tick_values[mass.value_throttled[0]]
    mass_max = mass_tick_values[mass.value_throttled[1]]
    mass_constraints = (DF["pl_massj"] >= mass_min.to('jupiterMass')) & (DF["pl_massj"] <= mass_max.to('jupiterMass'))
    radius_min = radius_tick_values[rad.value_throttled[0]]
    radius_max = radius_tick_values[rad.value_throttled[1]]
    radius_constraints = (DF["pl_radj"].value >= radius_min.to('jupiterRad')) & (DF["pl_radj"].value <= radius_max.to('jupiterRad'))
    per_min = 10**per.value_throttled[0]
    per_max = 10**per.value_throttled[1]
    per_constraints = (DF[axis_map["Orbital period"]].value>=per_min) & (DF[axis_map["Orbital period"]].value<=per_max)
    ecc_min = ecc.value_throttled[0]
    ecc_max = ecc.value_throttled[1]
    ecc_constraints = (DF[axis_map["Eccentricity"]]>=ecc_min) & (DF[axis_map["Eccentricity"]]<=ecc_max)
    teq_min = teq.value_throttled[0]
    teq_max = teq.value_throttled[1]
    teq_constraints = (DF[axis_map["Equilibrium temperature"]].value>=teq_min) & (DF[axis_map["Equilibrium temperature"]].value<=teq_max)
    teff_min = teff.value_throttled[0]
    teff_max = teff.value_throttled[1]
    teff_constraints = (DF[axis_map["Stellar Effective Temperature"]].value>=teff_min) & (DF[axis_map["Stellar Effective Temperature"]].value<=teff_max)
    mag_min = mag.value_throttled[0]
    mag_max = mag.value_throttled[1]
    mag_constraints = (DF[axis_map["Gaia magnitude"]]>=mag_min) & (DF[axis_map["Gaia magnitude"]]<=mag_max)
    Jmag_min = Jmag.value_throttled[0]
    Jmag_max = Jmag.value_throttled[1]
    Jmag_constraints = (DF["st_j"]>=Jmag_min) & (DF["st_j"]<=Jmag_max)
    # year_min = year.value_throttled[0]
    # year_max = year.value_throttled[1]
    # year_constraints = (DF[axis_map["Year of discovery"]]>=year_min) & (DF[axis_map["Year of discovery"]]<=year_max)



    DFS=DF[mass_constraints & radius_constraints & per_constraints & teq_constraints & teff_constraints & mag_constraints & ecc_constraints & Jmag_constraints]
    seltable.data = dict(x=DFS[x_name],y=DFS[y_name],P=DFS["pl_orbper"],Mp=DFS["planetmass"],Rp=DFS["planetradius"],T_eq=np.round(DFS["teq"],0),Gmag=np.round(DFS["gaia_gmag"],1),Jmag=np.round(DFS["st_j"],1),selcolor=DFS["selcolour"],alpha=DFS["alpha"],Name=DFS["pl_name"],rho=DFS['pl_dens'],ecc=DFS['pl_orbeccen'],FeH=DFS["st_metfe"])#All this additional info is needed ONLY for the tooltip. Just sayin.


    # for i in radius_constraints:
    #     print(i)

    # temp_constraints = (equilibrium_temperature < teq_max) & (equilibrium_temperature > teq_min)
    # rad_constraints = (rp < rad_max) & (rp > rad_min)
    # gmag_constaints = (g < gaia_mag_limit)
    # P_constraints = (P > P_min) & (P < P_max)
    # targets = transiting[temp_constraints & rad_constraints & gmag_constaints]
    # datatable.data = dict(x=DF[x_name],y=DF[y_name],P=DF["pl_orbper"],Mp=DF["planetmass"],Rp=DF["planetradius"],T_eq=DF["teq"],Gmag=DF["gaia_gmag"],color=DF["colour"],alpha=DF["alpha"],Name=DF["pl_name"])




#Finally, collect all the widgets and define when to call back.
selection = [mass,rad,per,ecc,teq,teff,mag,Jmag]#Left column.
axes = [x_axis,y_axis]
axis_options = [units,axis_log]


for param in axes:#If the value of any of the sliders or the axes changes, we update.
    param.on_change('value', lambda attr, old, new: update())
for param in selection:
    param.on_change('value_throttled', lambda attr, old, new: update_selection())

axis_log.on_change('active', lambda attr, old, new: change_logscale())
units.on_change('active', lambda attr, old, new: change_units())

rightcol = axes+axis_options#left column.
inputs1 = column(*selection, width=320, height=650)
inputs1.sizing_mode = "fixed"
inputs2 = column(*rightcol, width=280, height=650)
inputs2.sizing_mode = "fixed"
# inputs2 = row(*rightcol, width=280, height=650)
# inputs2.sizing_mode = "fixed"

desc = Div(text=open(join(dirname(__file__), "description.html")).read(), sizing_mode="stretch_width")
l = layout([[desc],[inputs1,p1,p2,p3,p4,inputs2],[Div(text='<i> by Jens Hoeijmakers (May 2020)</i>',sizing_mode="stretch_width")]], sizing_mode="scale_both")

change_logscale()
update()  # initial load of the data
update_selection()
curdoc().add_root(l)
curdoc().title = "Exoplanet Population"








#
# #Create boolean arrays for selecting the rows in the table, based on the above rules.
# temp_constraints = (equilibrium_temperature < teq_max) & (equilibrium_temperature > teq_min)
# rad_constraints = (rp < rad_max) & (rp > rad_min)
# gmag_constaints = (g < gaia_mag_limit)
# targets = transiting[temp_constraints & rad_constraints & gmag_constaints]#These are the highlighted planets.
# targets.sort('gaia_gmag')
# targets['r_earth'] = targets['pl_radj'].to(u.R_earth)
# targets[['pl_name', 'gaia_gmag', 'teq', 'r_earth', 'pl_orbper','st_rad','st_teff','st_spstr']].pprint(max_lines=1000)
#
#
#
# #Now we move on to plotting the population
#
# #These are rules for the planets that will be plotted as gray background points.
# has_rp = (rp > 0.0)#There needs to be a radius
# has_rs = (transiting['st_rad'] > 0)#...a stellar radius
# has_teff = (transiting['st_teff'] > 0)#... a stellar T_eff
# # is_spt = (transiting['st_spstr'].astype(str) == 'K2 V')#Test for being a particular spectral type. Will be needed to fill in systems with missing effective temperatures.
# systems_to_plot = transiting[has_rp & has_rs & has_teff]#Only transiting planets here.

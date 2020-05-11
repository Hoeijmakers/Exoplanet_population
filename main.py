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
import matplotlib.pyplot as plt
import astropy.units as u
from astroquery.nasa_exoplanet_archive import NasaExoplanetArchive
import copy
import sys
import numpy as np
from bokeh.io import curdoc, show, reset_output
from bokeh.layouts import column, layout
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
    transiting['alpha'] = 0.5

    transiting['planetradius'] = transiting['pl_radj']*1.0
    transiting['planetmass'] = transiting['pl_massj']*1.0
    return(transiting)

DF = prep_table()
# print(DF.colnames)
# sys.exit()

axis_map = {
    "Planet mass": "planetmass",
    "Planet radius": "planetradius",
    "Orbital period": "pl_orbper",
    "Equilibrium temperature": "teq",
    "Stellar Effective Temperature": "st_teff",
    "Gaia magnitude":"gaia_gmag",
    "Year of discovery": "pl_disc",
}
unit_map = {
    "Planet mass": "(Mj)",
    "Planet radius": "(Rj)",
    "Orbital period": "(d)",
    "Equilibrium temperature": "(K)",
    "Stellar Effective Temperature": "(K)",
    "Gaia magnitude":"",
    "Year of discovery": "",
}


desc = Div(text=open(join(dirname(__file__), "description.html")).read(), sizing_mode="stretch_width")

#Determine slider limits
lim_mass = (0,math.ceil(np.nanmax(DF['planetmass'])))
lim_year = (np.nanmin(DF["pl_disc"]),int(date.today().year))#Limit year between first discovery and now.
lim_mag  = (math.floor(np.nanmin(DF["gaia_gmag"])),math.ceil(np.max(DF["gaia_gmag"])))
# lim_teq  = (0,math.ceil(np.nanmax(DF['teq'].to('K').value)/1000.0)*1000.0)#Will need to deal with infinites here.
lim_teq = (0,6000)
# sys.exit()
lim_rad  = (0,math.ceil(np.nanmax(DF['planetradius'].to('jupiterRad').value)))
lim_teff = (0,math.ceil(np.nanmax(DF['st_teff'].to('K').value)/1000.0)*1000.0)
lim_per  = (0,math.ceil(np.nanmax(DF['pl_orbper'].to('d').value)/1000.0)*1000.0)

# Create sliders and other controls


mass = RangeSlider(start=lim_mass[0], end=lim_mass[1], value=lim_mass, step=.1, title=list(axis_map.keys())[0])
rad  = RangeSlider(start=lim_rad[0], end=lim_rad[1], value=lim_rad, step=.1, title=list(axis_map.keys())[1])
# per  = RangeSlider(start=lim_per[0], end=lim_per[1], value=lim_per, step=.1, title=list(axis_map.keys())[2])
per  = RangeSlider(start=-1.5,end=4, value=[-1.5,4], step=.01, title=list(axis_map.keys())[2],format=FuncTickFormatter(code="return (10**tick).toFixed(2)"))
teq  = RangeSlider(start=lim_teq[0], end=lim_teq[1], value=lim_teq, step=100, title=list(axis_map.keys())[3])
teff = RangeSlider(start=lim_teff[0], end=lim_teff[1], value=lim_teff, step=1000, title=list(axis_map.keys())[4])
mag  = RangeSlider(start=lim_mag[0], end=lim_mag[1], value=lim_mag, step=.1, title=list(axis_map.keys())[5])
year = RangeSlider(start=lim_year[0], end=lim_year[1], value=lim_year, step=1, title=list(axis_map.keys())[6])

#implement these.
# unit_options=
units = RadioGroup(labels=["Jupiter","Earth"], active=0)
axis_log = CheckboxGroup(labels=["log(x)", "log(y)"], active=[0])

# Type  =  Select(title="Type", value="All",options=['All','TOI','Transiting','Non-transiting (RV)','Directly imaged'])
x_axis = Select(title="X Axis", options=sorted(axis_map.keys()), value=list(axis_map.keys())[2])
y_axis = Select(title="Y Axis", options=sorted(axis_map.keys()), value=list(axis_map.keys())[1])




# Create Column Data Source that will be used by the plot.
# We create 2 tables. One that contains *all* planets; one that contains only the selected planets.
datatable = ColumnDataSource(data=dict(x=[],y=[],P=[],Rp=[], Mp=[], T_eff=[], Name=[], Year=[], T_eq=[], Gmag=[],color=[],alpha=[]))


axis_map = {
    "Planet mass": "planetmass",
    "Planet radius": "planetradius",
    "Orbital period": "pl_orbper",
    "Equilibrium temperature": "teq",
    "Stellar Effective Temperature": "st_teff",
    "Gaia magnitude":"gaia_gmag",
    "Year of discovery": "pl_disc",
}


TOOLTIPS=[("Name","@Name"),("Mass", "@Mp"),("Radius", "@Rp"),("P", "@P")]
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




# selected_table=copy.deepcopy(datatable)
# source.data = dict(
#     x=df[x_name],
#     y=df[y_name],
#     color=df["color"],
#     title=df["Title"],
#     year=df["Year"],
#     revenue=df["revenue"],
#     alpha=df["alpha"],
# )

#Create 4 figures with different combinations of xlog and ylog.
p1 = figure(plot_height=200, plot_width=200, title="", toolbar_location=None, sizing_mode="scale_height",tooltips=TOOLTIPS,x_axis_type="linear",y_axis_type='linear',visible=False)
p2 = figure(plot_height=200, plot_width=200, title="", toolbar_location=None, sizing_mode="scale_height",tooltips=TOOLTIPS,x_axis_type="log",y_axis_type='linear',visible=False)
p3 = figure(plot_height=200, plot_width=200, title="", toolbar_location=None, sizing_mode="scale_height",tooltips=TOOLTIPS,x_axis_type="linear",y_axis_type='log',visible=False)
p4 = figure(plot_height=200, plot_width=200, title="", toolbar_location=None, sizing_mode="scale_height",tooltips=TOOLTIPS,x_axis_type="log",y_axis_type='log',visible=False)
p1.circle(x="x", y="y", source=datatable, size=7, color="color", line_color=None, fill_alpha="alpha")
p2.circle(x="x", y="y", source=datatable, size=7, color="color", line_color=None, fill_alpha="alpha")
p3.circle(x="x", y="y", source=datatable, size=7, color="color", line_color=None, fill_alpha="alpha")
p4.circle(x="x", y="y", source=datatable, size=7, color="color", line_color=None, fill_alpha="alpha")
#All of them are set to invisible.


#CONTINUE HERE
# def select_movies():
#     genre_val = genre.value
#     director_val = director.value.strip()
#     cast_val = cast.value.strip()
#     selected = movies[
#         (movies.Reviews >= reviews.value) &
#         (movies.BoxOffice >= (boxoffice.value * 1e6)) &
#         (movies.Year >= min_year.value) &
#         (movies.Year <= max_year.value) &
#         (movies.Oscars >= oscars.value)
#     ]
#     if (genre_val != "All"):
#         selected = selected[selected.Genre.str.contains(genre_val)==True]
#     if (director_val != ""):
#         selected = selected[selected.Director.str.contains(director_val)==True]
#     if (cast_val != ""):
#         selected = selected[selected.Cast.str.contains(cast_val)==True]
#     return selected



def update():
    """This updates the axis labels and circles after changing the axes or selection sliders."""
    for p in [p1,p2,p3,p4]:
        p.xaxis.axis_label = x_axis.value+' '+unit_map[x_axis.value]
        p.yaxis.axis_label = y_axis.value+' '+unit_map[y_axis.value]
    x_name = axis_map[x_axis.value]
    y_name = axis_map[y_axis.value]
    #This is where the actual conversion between the exoplanet input table and the dataframe read by Bokeh is done.
    datatable.data = dict(x=DF[x_name],y=DF[y_name],P=DF["pl_orbper"],Mp=DF["planetmass"],Rp=DF["planetradius"],T_eq=DF["teq"],Gmag=DF["gaia_gmag"],color=DF["colour"],alpha=DF["alpha"],Name=DF["pl_name"])
    # print(units.active)


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
    p2.xaxis[0].formatter = FuncTickFormatter(code=fix_substring_JS)
    p3.yaxis[0].formatter = FuncTickFormatter(code=fix_substring_JS)
    p4.xaxis[0].formatter = FuncTickFormatter(code=fix_substring_JS)
    p4.yaxis[0].formatter = FuncTickFormatter(code=fix_substring_JS)
    #Wow. And it all still runs smoothly.


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


#Finally, collect all the widgets and define when to call back.
selection = [mass,rad,per,teq,teff,mag,year]#Left column.
axes = [x_axis,y_axis]
axis_options = [units,axis_log]


for param in selection+axes:#If the value of any of the sliders or the axes changes, we update.
    param.on_change('value', lambda attr, old, new: update())
axis_log.on_change('active', lambda attr, old, new: change_logscale())
units.on_change('active', lambda attr, old, new: change_units())

rightcol = axes+axis_options#left column.
inputs1 = column(*selection, width=320, height=650)
inputs1.sizing_mode = "fixed"
inputs2 = column(*rightcol, width=280, height=650)
inputs2.sizing_mode = "fixed"

l = layout([[desc],[inputs1,p1,p2,p3,p4,inputs2]], sizing_mode="scale_both")

change_logscale()
update()  # initial load of the data
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

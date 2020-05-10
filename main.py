# This is the file that is executed by the bokeh server.
# """This plots the exoplanet population to create a plot of selectable planets
# in the exoplanet population, using the interactive Bokeh server.
#
# It is based off a Gist by Brett Morris (github bmorris3), pulling it from
# Notebook form and adding an interactive plot.
#
# Jens Hoeijmakers, 05-05-2020
#
# This is grafted onto https://github.com/bokeh/bokeh/blob/master/examples/app/movies/main.py"""
import numpy as np
import matplotlib.pyplot as plt
import astropy.units as u
from astroquery.nasa_exoplanet_archive import NasaExoplanetArchive
import copy
import sys
import numpy as np
from bokeh.io import curdoc
from bokeh.layouts import column, layout
from bokeh.models import ColumnDataSource, Div, Select, Slider, TextInput,RangeSlider,RadioGroup,CheckboxGroup
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

axis_map = {
    "Planet mass": "planetmass",
    "Planet radius": "planetradius",
    "Orbital period (d)": "pl_orbper",
    "Equilibrium temperature (K)": "teq",
    "Stellar Effective Temperature": "st_teff",
    "Gaia magnitude":"gaia_gmag",
    "Year of discovery": "pl_disc",
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
per  = RangeSlider(start=lim_per[0], end=lim_per[1], value=lim_per, step=.1, title=list(axis_map.keys())[2])
teq  = RangeSlider(start=lim_teq[0], end=lim_teq[1], value=lim_teq, step=100, title=list(axis_map.keys())[3])
teff = RangeSlider(start=lim_teff[0], end=lim_teff[1], value=lim_teff, step=1000, title=list(axis_map.keys())[4])
mag  = RangeSlider(start=lim_mag[0], end=lim_mag[1], value=lim_mag, step=.1, title=list(axis_map.keys())[5])
year = RangeSlider(start=lim_year[0], end=lim_year[1], value=lim_year, step=1, title=list(axis_map.keys())[6])

#implement these.
units = RadioGroup(labels=["Jupiter","Earth"], active=0)
axis_log = CheckboxGroup(labels=["log(x)", "log(y)"], active=[0,0])

# Type  =  Select(title="Type", value="All",options=['All','TOI','Transiting','Non-transiting (RV)','Directly imaged'])
x_axis = Select(title="X Axis", options=sorted(axis_map.keys()), value=list(axis_map.keys())[2])
y_axis = Select(title="Y Axis", options=sorted(axis_map.keys()), value=list(axis_map.keys())[1])






# Create Column Data Source that will be used by the plot.
# We create 2 tables. One that contains *all* planets; one that contains only the selected planets.
datatable = ColumnDataSource(data=dict(x=[],y=[],P=[],Rp=[], Mp=[], T_eff=[], Name=[], Year=[], T_eq=[], Gmag=[],color=[],alpha=[]))
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


p = figure(plot_height=200, plot_width=200, title="", toolbar_location=None, sizing_mode="scale_height",x_axis_type="log")
p.circle(x="x", y="y", source=datatable, size=7, color="color", line_color=None, fill_alpha="alpha")




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
    #Put all the selected planets into the data structure.
    # df = select_movies()
    x_name = axis_map[x_axis.value]
    y_name = axis_map[y_axis.value]
    p.xaxis.axis_label = x_axis.value
    p.yaxis.axis_label = y_axis.value
    # p.title.text = "%d movies selected" % len(df)
    datatable.data = dict(x=DF[x_name],y=DF[y_name],P=DF["pl_orbper"],Rp=DF["pl_radj"],T_eq=DF["teq"],Gmag=DF["gaia_gmag"],color=DF["colour"],alpha=DF["alpha"])
    # print(units.active)
    # print(axis_log.active)

controls = [mass,rad,per,teq,teff,mag,year,x_axis,y_axis]
for control in controls:
    control.on_change('value', lambda attr, old, new: update())

inputs = column(*controls, width=320, height=700)
inputs.sizing_mode = "fixed"
l = layout([[desc],[inputs, p]], sizing_mode="scale_both")


update()  # initial load of the data
curdoc().add_root(l)
curdoc().title = "Planets"








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

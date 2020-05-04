def plot_population():
    """This plots the exoplanet population to create a plot of selectable planets
    in the exoplanet population

    It is based off a Gist by Brett Morris (github bmorris3), pulling it from
    Notebook form and adding an interactive plot.

    Jens Hoeijmakers, 04-05-2020"""
    import numpy as np
    import matplotlib.pyplot as plt
    import astropy.units as u
    from astroquery.nasa_exoplanet_archive import NasaExoplanetArchive


    #First establish the rules that a planet must satisfy in order to be printed / highlighted.
    teq_min = 1000 * u.K
    teq_max = 1300 * u.K
    rad_min = 2 * u.R_earth
    rad_max = 4 * u.R_earth
    gaia_mag_limit = 13

    #Read the archive and compute the equilibrium temperature.
    #TO DO: SOME PLANETS FALL OUT BECAUSE THEY DONT HAVE A STELLAR EFFECTIVE TEMPERATURE AND/OR STELLAR RADIUS.
    #HOWEVER THESE CAN BE APPROXIMATED FROM THE SPECTRAL TYPE. FOR EACH MISSING VALUE, I NEED TO LOOK UP WHAT A STAR WITH
    #THAT SPECTRAL TYPE TYPICALLY HAS FOR VALUES OF R_S AND T_EFF, AND REPLACE THOSE.
    table = NasaExoplanetArchive.get_confirmed_planets_table(all_columns=True)#This is an astropy table.
    transiting = table[(table['pl_tranflag'].data).astype(bool)]#Select only the transiting ones, and put them in a new table.
    rp = transiting['pl_radj']#Short-hand for planet radii.
    equilibrium_temperature = (transiting['st_teff'] * np.sqrt(transiting['st_rad'] / 2 / transiting['pl_orbsmax'])).decompose()#Compute T_eq.
    g = transiting['gaia_gmag'].quantity#Short-hand for the Gaia magnitude.
    transiting['teq'] = equilibrium_temperature

    #Create boolean arrays for selecting the rows in the table, based on the above rules.
    temp_constraints = (equilibrium_temperature < teq_max) & (equilibrium_temperature > teq_min)
    rad_constraints = (rp < rad_max) & (rp > rad_min)
    gmag_constaints = (g < gaia_mag_limit)
    targets = transiting[temp_constraints & rad_constraints & gmag_constaints]#These are the highlighted planets.
    targets.sort('gaia_gmag')
    targets['r_earth'] = targets['pl_radj'].to(u.R_earth)
    targets[['pl_name', 'gaia_gmag', 'teq', 'r_earth', 'pl_orbper','st_rad','st_teff','st_spstr']].pprint(max_lines=1000)



    #Now we move on to plotting the population

    #These are rules for the planets that will be plotted as gray background points.
    has_rp = (rp > 0.0)#There needs to be a radius
    has_rs = (transiting['st_rad'] > 0)#...a stellar radius
    has_teff = (transiting['st_teff'] > 0)#... a stellar T_eff
    # is_spt = (transiting['st_spstr'].astype(str) == 'K2 V')#Test for being a particular spectral type. Will be needed to fill in systems with missing effective temperatures.
    systems_to_plot = transiting[has_rp & has_rs & has_teff]#Only transiting planets here.

    fig,ax = plt.subplots()
    sc = plt.scatter(systems_to_plot['teq'],systems_to_plot['pl_radj'].to(u.R_earth),c='gray',s=20,alpha=0.5)
    sct=plt.scatter(targets['teq'],targets['pl_radj'].to(u.R_earth),c='orange',s=20,alpha=0.5)
    ax.set_ylabel('Planet radius')
    ax.set_xlabel('Equilibrium temperature')
    ax.set_title('Temperature vs radius plot')
    ax.set_xlim(ax.get_xlim()[::-1])


    #And this is all annotation, taken from :
    annot = ax.annotate("", xy=(0,0), xytext=(20,20),textcoords="offset points",bbox=dict(boxstyle="round", fc="w"),arrowprops=dict(arrowstyle="->"))
    annot.set_visible(False)
    names = systems_to_plot['pl_name']
    gmags = systems_to_plot['gaia_gmag']
    Ps = systems_to_plot['pl_orbper']
    def update_annot_new(ind):
        pos = sc.get_offsets()[ind["ind"][0]]
        annot.xy = pos
        text=''
        n_in = len(ind["ind"])
        prefix=''#This becomes a newline if the forloop is run through more than once.
        for n in ind["ind"]:
            text+=prefix+names[n]+'\n'
            text+='     G = %s \n'%np.round(gmags[n],2)
            text+='     P = %s'%np.round(Ps[n],2)
            prefix='\n'
        # text = "{}, {}".format(" ".join(list(map(str,ind["ind"])))," ".join([names[n] for n in ind["ind"]]))
        annot.set_text(text)
        annot.get_bbox_patch().set_alpha(0.4)
    def newhover(event):
        vis = annot.get_visible()
        if event.inaxes == ax:
            cont, ind = sc.contains(event)
            if cont:
                update_annot_new(ind)
                annot.set_visible(True)
                fig.canvas.draw_idle()
            else:
                if vis:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()
    fig.canvas.mpl_connect("motion_notify_event", newhover)
    plt.show()
plot_population()

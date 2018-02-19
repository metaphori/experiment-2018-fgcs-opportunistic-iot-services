import numpy as np
import xarray as xr
import re

def distance(val, ref):
    return abs(ref - val)
vectDistance = np.vectorize(distance)

def getClosest(sortedMatrix, column, val):
    while len(sortedMatrix) > 3:
        half = int(len(sortedMatrix) / 2)
        sortedMatrix = sortedMatrix[-half - 1:] if sortedMatrix[half, column] < val else sortedMatrix[: half + 1]
    if len(sortedMatrix) == 1:
        result = sortedMatrix[0].copy()
        result[column] = val
        return result
    else:
        safecopy = sortedMatrix.copy()
        safecopy[:, column] = vectDistance(safecopy[:, column], val)
        minidx = np.argmin(safecopy[:, column])
        safecopy = safecopy[minidx, :].A1
        safecopy[column] = val
        return safecopy

def convert(column, samples, matrix):
    return np.matrix([getClosest(matrix, column, t) for t in samples])

def valueOrEmptySet(k, d):
    return (d[k] if isinstance(d[k], set) else {d[k]}) if k in d else set()

def mergeDicts(d1, d2):
    """
    Creates a new dictionary whose keys are the union of the keys of two
    dictionaries, and whose values are the union of values.

    Parameters
    ----------
    d1: dict
        dictionary whose values are sets
    d2: dict
        dictionary whose values are sets

    Returns
    -------
    dict
        A dict whose keys are the union of the keys of two dictionaries,
    and whose values are the union of values

    """
    res = {}
    for k in d1.keys() | d2.keys():
        res[k] = valueOrEmptySet(k, d1) | valueOrEmptySet(k, d2)
    return res

def extractCoordinates(filename):
    """
    Scans the header of an Alchemist file in search of the variables.

    Parameters
    ----------
    filename : str
        path to the target file
    mergewith : dict
        a dictionary whose dimensions will be merged with the returned one

    Returns
    -------
    dict
        A dictionary whose keys are strings (coordinate name) and values are
        lists (set of variable values)

    """
    with open(filename, 'r') as file:
        regex = re.compile(' (?P<varName>[a-zA-Z]+) = (?P<varValue>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?),?')
        dataBegin = re.compile('\d')
        for line in file:
            match = regex.findall(line)
            if match:
                return {var : float(value) for var, value in match}
            elif dataBegin.match(line[0]):
                return {}

def extractVariableNames(filename):
    """
    Gets the variable names from the Alchemist data files header.

    Parameters
    ----------
    filename : str
        path to the target file

    Returns
    -------
    list of list
        A matrix with the values of the csv file

    """
    with open(filename, 'r') as file:
        dataBegin = re.compile('\d')
        lastHeaderLine = ''
        for line in file:
            if dataBegin.match(line[0]):
                break
            else:
                lastHeaderLine = line
        if lastHeaderLine:
            regex = re.compile(' (?P<varName>\S+)')
            return regex.findall(lastHeaderLine)
        return []

def openCsv(path):
    """
    Converts an Alchemist export file into a list of lists representing the matrix of values.

    Parameters
    ----------
    path : str
        path to the target file

    Returns
    -------
    list of list
        A matrix with the values of the csv file

    """
    regex = re.compile('\d')
    with open(path, 'r') as file:
        lines = filter(lambda x: regex.match(x[0]), file.readlines())
        return [[float(x) for x in line.split()] for line in lines]

if __name__ == '__main__':
    # CONFIGURE SCRIPT
    directory = 'data'
    pickleOutput = 'data_summary'
    experiments = ['vienna']
    floatPrecision = '{: 0.2f}'
    seedVars = ['seed']
    timeSamples = 1000
    minTime = 0
    maxTime = 7200
    timeColumnName = 'time'
    logarithmicTime = False
    
    # Setup libraries
    np.set_printoptions(formatter={'float': floatPrecision.format})
    # Read the last time the data was processed, reprocess only if new data exists, otherwise just load
    import pickle
    import os
    newestFileTime = max(os.path.getmtime(directory + '/' + file) for file in os.listdir(directory))
    try:
        lastTimeProcessed = pickle.load(open('timeprocessed', 'rb'))
    except:
        lastTimeProcessed = -1
    shouldRecompute = newestFileTime != lastTimeProcessed
    if not shouldRecompute:
        try:
            means = pickle.load(open(pickleOutput + '_mean', 'rb'))
            stdevs = pickle.load(open(pickleOutput + '_std', 'rb'))
        except:
            shouldRecompute = True
    if shouldRecompute:
        timefun = np.logspace if logarithmicTime else np.linspace
        means = {}
        stdevs = {}
        for experiment in experiments:
            # Collect all files for the experiment of interest
            import fnmatch
            allfiles = filter(lambda file: fnmatch.fnmatch(file, experiment + '_*.txt'), os.listdir(directory))
            allfiles = [directory + '/' + name for name in allfiles]
            allfiles.sort()
            # From the file name, extract the independent variables
            dimensions = {}
            for file in allfiles:
                dimensions = mergeDicts(dimensions, extractCoordinates(file))
            dimensions = {k: sorted(v) for k, v in dimensions.items()}
            # Add time to the independent variables
            dimensions[timeColumnName] = range(0, timeSamples)
            # Compute the matrix shape
            shape = tuple(len(v) for k, v in dimensions.items())
            # Prepare the Dataset
            dataset = xr.Dataset()
            for k, v in dimensions.items():
                dataset.coords[k] = v
            varNames = extractVariableNames(allfiles[0])
            for v in varNames:
                if v != timeColumnName:
                    novals = np.ndarray(shape)
                    novals.fill(float('nan'))
                    dataset[v] = (dimensions.keys(), novals)
            # Compute maximum and minimum time, create the resample
            timeColumn = varNames.index(timeColumnName)
            allData = { file: np.matrix(openCsv(file)) for file in allfiles }
            computeMin = minTime is None
            computeMax = maxTime is None
            if computeMax:
                maxTime = float('-inf')
                for data in allData.values():
                    maxTime = max(maxTime, data[-1, timeColumn])
            if computeMin:
                minTime = float('inf')
                for data in allData.values():
                    minTime = min(minTime, data[0, timeColumn])
            timeline = timefun(minTime, maxTime, timeSamples)
            # Resample
            for file in allData:
                allData[file] = convert(timeColumn, timeline, allData[file])
            # Populate the dataset
            for file, data in allData.items():
                dataset[timeColumnName] = timeline
                for idx, v in enumerate(varNames):
                    if v != timeColumnName:
                        darray = dataset[v]
                        experimentVars = extractCoordinates(file)
                        darray.loc[experimentVars] = data[:, idx].A1
            # Fold the dataset along the seed variables, producing the mean and stdev datasets
            means[experiment] = dataset.mean(seedVars)
            stdevs[experiment] = dataset.std(seedVars)
        # Save the datasets
        pickle.dump(means, open(pickleOutput + '_mean', 'wb'), protocol=-1)
        pickle.dump(stdevs, open(pickleOutput + '_std', 'wb'), protocol=-1)
        pickle.dump(newestFileTime, open('timeprocessed', 'wb'))





    # Prepare the charting system
    import matplotlib
    import matplotlib.pyplot as plt
    import matplotlib.cm as cmx
    figure_size=(6, 3)
    colormap = cmx.gist_rainbow
    means['vienna']['CurrentSpeed[Sum]'] = means['vienna']['CurrentSpeed[Sum]'] / 1497
    for datavar in means['vienna'].data_vars:
        fig = plt.figure(figsize = figure_size)
        ax = fig.add_subplot(1, 1, 1)
        matrix = means['vienna'][datavar]
        titles = {
            '@following[Sum]': 'Users being steered',
            '@overcrowded[Sum]': 'Users in dangerous areas',
            '@risk[Sum]': 'Users in moderate risk areas',
            '@warning[Sum]': 'Users in warning zone',
            '@direction[Sum]': 'Users receiving steering information',
            '@crowd[Sum]': 'Users receiving the warning alert',
            'CurrentSpeed[Sum]': 'Mean walking speed',
            'DistanceTraveled[Sum]': 'Mean walked distance',
            'OverallDistanceTraveled[Sum]': 'Mean total walked distance'
        }
        title = titles[datavar]
        ax.set_title(title)
        x = matrix.coords[timeColumnName] / 60 
        maxy = float('-inf')
        miny = float('inf')
        for dimension in matrix.coords:
            if dimension != timeColumnName:
                for index, dimval in enumerate(matrix.coords[dimension]):
                    y = matrix.loc[{dimension: dimval}]
                    maxy = max(maxy, y.where(getattr(y, timeColumnName) > 20 * 60).max() * 1.1)
                    miny = min(miny, y.min() * 0.9)
                    ax.set_ylabel('speed (m/s)' if 'Speed' in datavar else 'distance traveled (m)' if 'Distance' in datavar else 'people')
                    ax.set_xlabel('time (simulated minutes)')
                    color = colormap(index / len(matrix.coords[dimension]))
                    ax.plot(x, y, color = color, label = 'p = ' + "{0:.1f}".format(float(dimval)))
        ax.set_xlim(x.min(), x.max())
        ax.set_ylim(miny, maxy)
        ax.legend(shadow=True, bbox_to_anchor=[1, 1.05])
        fig.savefig(title.replace(' ', '_') + '.pdf', bbox_inches=matplotlib.transforms.Bbox([[0, -0.05], [6.52, 2.9]]))
   
    # Aggregate chart: average of users in danger and their speed with probability of following the advice
    data = means['vienna']['@overcrowded[Sum]'].mean('time')
    dataerr = means['vienna']['@overcrowded[Sum]'].std('time')
    dataspeed = means['vienna']['CurrentSpeed[Sum]'].mean('time')
    dataspeederr = means['vienna']['CurrentSpeed[Sum]'].std('time')
    x = data.coords['pFollows']
    fig = plt.figure(figsize = figure_size)
    ax = fig.add_subplot(1, 1, 1)
    ax2 = ax.twinx()
    title = 'Cost-benefit: average mean speed and people in danger'
    ax.set_title(title)
    errline = ax.plot(x, data + dataerr, color='black', linestyle='--', linewidth=1, label='± standard deviation')
    ax.plot(x, data - dataerr, color='black', linestyle='--', linewidth=1)
    print(dataspeederr)
    ax2.plot(x, dataspeed + dataspeederr, color='red', linestyle='--', linewidth=1)
    ax2.plot(x, dataspeed - dataspeederr, color='red', linestyle='--', linewidth=1)
    line1 = ax.plot(x, data, color='black', label='People in danger')
    line2 = ax2.plot(x, dataspeed, color = 'red', label='Mean people speed')
    ax.set_ylabel('People')
    ax.set_xlabel('Probability of users following the app advice')
    ax2.set_ylabel('Mean people speed (m/s)')
    ax2.set_ylim(0, (dataspeed + dataspeederr).max() * 1.1)
    ax.set_ylim(0, (data + dataerr).max() * 1.1)
    ax.set_xlim(0, 1)
    lines = line1 + errline + line2
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, shadow=False, frameon=False, ncol=2, bbox_to_anchor=[0.05, 0.75])
    fig.savefig('summary.pdf', bbox_inches=matplotlib.transforms.Bbox([[0.25, -0.05], [5.95, 2.9]]))


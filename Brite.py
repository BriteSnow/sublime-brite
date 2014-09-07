import os
import sublime, sublime_plugin

COMMAND_LABELS = [["New view asset(s)","Create the new britejs view .js, .less, .tmpl assets or the missing one(s)"],
								 ["List views","List all britejs views"]]

COMMANDS = [{"cmd":"brite_new_view"},
						{"cmd":"brite_list_views"}]

VIEW_DIRS = set(["js","tmpl","less"])

SNIPPETS = {"js":"Packages/Brite/brite-view-js.sublime-snippet",
						"tmpl":"Packages/Brite/brite-view-tmpl.sublime-snippet",
						"less":"Packages/Brite/brite-view-less.sublime-snippet"}

OPENING_ORDER = ["less","js","tmpl"]

DISPLAY_ORDER = ["js","tmpl","less"]						

# --------- CMD: brite HOME --------- #
class BriteCommand(sublime_plugin.WindowCommand):
	def run(self):
		# by default, we copy the static commands
		self.cmdLabels = [] + COMMAND_LABELS
		self.cmds = [] + COMMANDS

		# check if the activeView is a brite.js view for additional commands
		activeView = self.window.active_view()
		viewFile = activeView.file_name()
		viewName = os.path.splitext(os.path.basename(viewFile))[0]
		if viewName[0].isupper():
			baseDir = find_view_base_dir(viewFile)
			viewInfo = build_view_info(baseDir,viewName,self.window)

			# We offer to open the remaining files
			unopenedTypes = viewInfo['unopenedTypes'];
			if (len(unopenedTypes) > 0):
				label = ["Open other " + viewName + " assets"];
				# label.append("Openning " + ", ".join(map(lambda t: viewName + "." + t,unopenedTypes)))
				label.append("Opening " + display_assets(viewName,unopenedTypes))
				self.cmdLabels.append(label)
				self.cmds.append({"cmd":"brite_open_unopened","args":{"viewInfo":viewInfo}})

			absentTypes = viewInfo['absentTypes']
			if (len(absentTypes) > 0):
				label = ["Create missing " + viewName + " assets"];
				label.append("Creating " + display_assets(viewName,absentTypes))
				self.cmdLabels.append(label)
				self.cmds.append({"cmd":"brite_create_absents","args":{"viewInfo":viewInfo}})				

		self.window.show_quick_panel(self.cmdLabels,self.on_brite_done)

	def on_brite_done(self, idx):
		if idx >= 0:
			cmd = self.cmds[idx]['cmd']
			args = self.cmds[idx].get('args')
			self.window.run_command(cmd,args)
# --------- /CMD: brite HOME --------- #

# --------- CMD: brite_run_snippet --------- #
class BriteRunSnippet(sublime_plugin.TextCommand):
	def run(self, edit, **args):
		print(self.view,args)
		viewName = args["viewName"]
		itemType = args["itemType"]
		snippet = SNIPPETS[itemType]
		def snip():
			self.view.run_command("insert_snippet",{"name":snippet})
			self.view.run_command("insert", {"characters": viewName})
			self.view.run_command("next_field")
		sublime.set_timeout(snip,10)
# --------- /CMD: brite_run_snippet --------- #
		
# --------- CMD: brite_new_view --------- #
class BriteNewViewCommand(sublime_plugin.WindowCommand):
	def run(self):
		v = self.window.show_input_panel("Enter ViewName:","",self.on_name_input_done,
																			self.on_name_input_change,
																			self.on_name_input_cancel)
		print(v,v.name())

	def on_name_input_done(self,viewName):
		activeView = self.window.active_view()
		activeView.erase_status("britemsg")
		viewFile = activeView.file_name()
		baseDir = find_view_base_dir(viewFile)
		viewInfo = build_view_info(baseDir,viewName,self.window)

		typesToIgnore = viewInfo["existingTypes"]
		if len(typesToIgnore) > 0:
			msg = ", ".join(map(lambda t: viewName + "." + t,typesToIgnore))
			msg += " files already exist, ignoring them." 
			sublime.status_message(msg)

		create_view_items(viewInfo,self.window)

	def on_name_input_change(self,viewName):
		activeView = self.window.active_view()
		viewFile = activeView.file_name()
		baseDir = find_view_base_dir(viewFile)
		viewInfo = build_view_info(baseDir,viewName,self.window)
		msg = "Will create: "
		msg += ", ".join(map(lambda i: i["shortFileName"],viewInfo["absentItems"]))
		existingItems = viewInfo["existingItems"]
		if len(existingItems) > 0:
			msg += " (already exist: " + ", ".join(map(lambda i: i["shortFileName"],existingItems)) + ")"
		activeView.set_status("britemsg",msg)

	def on_name_input_cancel(self):
		activeView = self.window.active_view()
		activeView.erase_status("britemsg")
# --------- /CMD: brite_new_view --------- #
		

# --------- CMD: brite_list_views --------- #
class BriteListViewsCommand(sublime_plugin.WindowCommand):
	def run(self):
		activeView = self.window.active_view()
		viewFile = activeView.file_name()
		baseDir = find_view_base_dir(viewFile)
		self.viewInfoList = self.list_viewInfo(baseDir);

		def viewListItemFromViewInfo(viewInfo):
			viewListItem = []
			viewListItem.append(viewInfo['name'])
			viewListItem.append(" | ".join(map(lambda t: t.upper(), viewInfo['existingTypes'])))
			return viewListItem
		
		viewList = list(map(viewListItemFromViewInfo,self.viewInfoList ))
		sublime.set_timeout(lambda: self.window.show_quick_panel(viewList,self.on_list_views_done), 100)
		
		
	def on_list_views_done(self,idx):
		if idx > -1:
			viewInfo = self.viewInfoList[idx]
			open_view_items(viewInfo,self.window)

	# Return a [{viewInfo}]
	def list_viewInfo(self,baseDir):
		jsViews = self.get_viewnames_set(os.path.join(baseDir,"js/"))
		viewInfoList = []
		for name in jsViews:
			viewInfo = build_view_info(baseDir,name,self.window)
			viewInfoList.append(viewInfo)
		return viewInfoList

	def get_viewnames_set(self,assetDir):
		viewNames = set()
		for name in os.listdir(assetDir):
			if name[0].isupper():
				viewNames.add(os.path.splitext(name)[0])
		viewNames = sorted(viewNames)
		return viewNames
# --------- /CMD: brite_list_views --------- #

# --------- CMD: brite_create_absents --------- #
class BriteCreateAbsentsCommand(sublime_plugin.WindowCommand):
	def run(self, **args):
		viewInfo = args['viewInfo']
		create_view_items(viewInfo,self.window)

# --------- /CMD: brite_create_absents --------- #

# --------- CMD: brite_open_unopened --------- #
# Command that open the unopened assets for a give viewInfo
class BriteOpenUnopened(sublime_plugin.WindowCommand):
	def run(self, **args):
		viewInfo = args['viewInfo']
		open_view_items(viewInfo,self.window,True)

# --------- /CMD: brite_open_unopened --------- #

# --------- Utils: display --------- #
def display_assets(viewName,types,withPath = False):
	txts = []
	typeSet = set(types)
	for t in DISPLAY_ORDER:
		if t in typeSet:
			txt = t + "/" if withPath else ""
			txt += viewName + "." + t
			txts.append(txt)
	return ", ".join(txts)

# --------- /Utils: display --------- #

# --------- Utils: open & create view assets --------- #
def open_view_items(viewInfo,window,onlyUnopened = False):
	multiGroup = window.num_groups() > 1
	for itemType in OPENING_ORDER:
		item = viewInfo['items'][itemType]
		if item['exists'] & (onlyUnopened & item['opened'] == False):
			v = window.open_file(item['file'])
			if multiGroup & (item['type'] == "tmpl"):
				window.set_view_index(v, 1,0)

def create_view_items(viewInfo,window):
	multiGroup = window.num_groups() > 1
	viewInfoItems = viewInfo['items']
	viewName = viewInfo['name']

	for itemType in OPENING_ORDER: 
		item = viewInfoItems[itemType]
		if item['exists'] == False:
			f = item["file"]
			itemType = item["type"]
			v = window.open_file(f)
			args = {"viewName":viewName,
							"itemType":itemType}
			v.run_command("brite_run_snippet",args)
			if multiGroup & (itemType == "tmpl"):
				window.set_view_index(v, 1,0)	
# --------- /Utils: open & create view assets --------- #

# --------- Utils: find viewInfo --------- #
def build_view_info(baseDir,viewName, window):
	fileDic = {}
	fileDic['less'] = os.path.join(baseDir,"less/",viewName + ".less")
	fileDic['js'] = os.path.join(baseDir,"js/",viewName + ".js")
	fileDic['tmpl'] = os.path.join(baseDir,"tmpl/",viewName + ".tmpl")
	viewInfo = {"name":viewName,
							"items":{},
							"existingItems":[],
							"absentItems":[],
							"existingTypes": [],
							"absentTypes": [],
							"openedTypes":[],
							"unopenedTypes": []}
	for itemType in fileDic:
		item = {"type":itemType}
		item['file'] = fileDic[itemType]
		item['shortFileName'] = itemType + "/" + viewName + "." + itemType
		exists = os.path.exists(fileDic[itemType])
		item['exists'] = exists
		if exists:
			viewInfo['existingItems'].append(item)
			viewInfo['existingTypes'].append(itemType)
		else:
			viewInfo['absentItems'].append(item)
			viewInfo['absentTypes'].append(itemType)
		isopen = (window.find_open_file(item['file']) != None)
		item['opened'] = isopen	
		if isopen:
			viewInfo['openedTypes'].append(itemType)
		else:
			if exists:
				viewInfo['unopenedTypes'].append(itemType)
		viewInfo['items'][itemType] = item

	viewInfo['existingTypes'] = sort_types_for_display(viewInfo['existingTypes'])
	viewInfo['absentTypes'] = sort_types_for_display(viewInfo['absentTypes'])
	viewInfo['openedTypes'] = sort_types_for_display(viewInfo['openedTypes'])	
	viewInfo['unopenedTypes'] = sort_types_for_display(viewInfo['unopenedTypes'])	
	return viewInfo

def sort_types_for_display(types):
	ntypes = []
	print("types",types)
	s = set(types)
	for t in DISPLAY_ORDER:
		if t in s:
			ntypes.append(t)
	return ntypes


# --------- /Utils: find views --------- #

# --------- Utils: find view base dir --------- #
def find_view_base_dir(viewFile):
	dir = get_dir(viewFile);
	baseDir = get_base_dir(dir);
	# if the baseDir is null, we need to look some more
	if baseDir == None:
		for dirName, subdirList, fileList in os.walk(dir):
			for name in subdirList:
				if name in VIEW_DIRS:
					return dirName
		return None
	else:
		return baseDir


# Returns the base dir if it can deduct it, otherwise, None
def get_base_dir(dir):
	name = os.path.basename(dir)
	if name in VIEW_DIRS:
		return os.path.dirname(dir)
	else:
		return None

# returns the file if file is a dir, otherwise, returns the dir of this file
def get_dir(file):
	if os.path.isdir(file) == False:
		return os.path.dirname(file)
	else:
		return file
# --------- /Utils: find view base dir --------- #




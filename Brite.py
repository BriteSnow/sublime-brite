import os
import sublime, sublime_plugin

COMMAND_LABELS = [["New view asset(s)","Create the new britejs view .js, .less, .tmpl assets or the missing one(s)"],
								 ["List views","List all britejs views"]]

COMMAND_IDX_NAMES = {0:"brite_new_view",
										 1:"brite_list_views"}

VIEW_DIRS = set(["js","tmpl","less"])

SNIPPETS = {"js":"Packages/Brite/brite-view-js.sublime-snippet",
						"tmpl":"Packages/Brite/brite-view-tmpl.sublime-snippet",
						"less":"Packages/Brite/brite-view-less.sublime-snippet"}

OPENING_ORDER = ["less","js","tmpl"]						

# --------- CMD: brite HOME --------- #
class BriteCommand(sublime_plugin.WindowCommand):
	def run(self):
		# by default, we take the static commands
		self.cmdLabels = COMMAND_LABELS
		self.cmdIdx = COMMAND_IDX_NAMES

		# check if the activeView is a brite.js view for additional commands
		activeView = self.window.active_view()
		viewFile = activeView.file_name()
		viewName = os.path.splitext(os.path.basename(viewFile))[0]
		if viewName[0].isupper():
			baseDir = find_view_base_dir(viewFile)
			viewInfo = build_view_info(baseDir,viewName)
			# TODO: Needs to complete

		self.window.show_quick_panel(self.cmdLabels,self.on_brite_done)

	def on_brite_done(self, idx):
		if idx >= 0:
			cmd = self.cmdIdx[idx]
			self.window.run_command(cmd)
# --------- /CMD: brite HOME --------- #

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
		viewInfo = build_view_info(baseDir,viewName)
		viewInfoItems = viewInfo["items"]
		itemsToCreate = viewInfo["absentItems"]
		itemsToIgnore = viewInfo["existingItems"]

		if len(itemsToIgnore) > 0:
			msg = ", ".join(map(lambda item: viewName + "." + item["type"],itemsToIgnore))
			msg += " files already exist, ignoring them." 
			sublime.status_message(msg)

		if len(itemsToCreate) > 0:
			multiGroup = self.window.num_groups() > 1
			for itemType in OPENING_ORDER: 
				item = viewInfoItems[itemType]
				if item['exists'] == False:
					f = item["file"]
					itemType = item["type"]
					v = self.window.open_file(f)
					args = {"viewName":viewName,
									"itemType":itemType}
					v.run_command("brite_run_snippet",args)
					if multiGroup & (itemType == "tmpl"):
						self.window.set_view_index(v, 1,0)

	def on_name_input_change(self,viewName):
		activeView = self.window.active_view()
		viewFile = activeView.file_name()
		baseDir = find_view_base_dir(viewFile)
		viewInfo = build_view_info(baseDir,viewName)
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
			viewListItem.append(viewInfo["name"])
			viewListItem.append(", ".join(map(lambda i: i['shortFileName'],viewInfo['existingItems'])))
			return viewListItem
		
		viewList = list(map(viewListItemFromViewInfo,self.viewInfoList ))
		sublime.set_timeout(lambda: self.window.show_quick_panel(viewList,self.on_list_views_done), 100)
		
		
	def on_list_views_done(self,idx):
		if idx > -1:
			viewInfo = self.viewInfoList[idx]
			multiGroup = self.window.num_groups() > 1
			for itemType in OPENING_ORDER:
				item = viewInfo['items'][itemType]
				if item['exists']:
					v = self.window.open_file(item['file'])
					if multiGroup & (item['type'] == "tmpl"):
						self.window.set_view_index(v, 1,0)

	# Return a [{viewInfo}]
	def list_viewInfo(self,baseDir):
		jsViews = self.fill_set(os.path.join(baseDir,"js/"),set())
		jsViews = sorted(jsViews)
		viewInfoList = []
		for name in jsViews:
			viewInfo = build_view_info(baseDir,name)
			viewInfoList.append(viewInfo)
		return viewInfoList

	def fill_set(self,assetDir,viewSet):
		for name in os.listdir(assetDir):
			if name[0].isupper():
				viewSet.add(os.path.splitext(name)[0])
		return viewSet

# --------- /CMD: brite_list_views --------- #

# --------- Module Functions: find viewInfo --------- #

def build_view_info(baseDir,viewName):
	fileDic = {}
	fileDic['less'] = os.path.join(baseDir,"less/",viewName + ".less")
	fileDic['js'] = os.path.join(baseDir,"js/",viewName + ".js")
	fileDic['tmpl'] = os.path.join(baseDir,"tmpl/",viewName + ".tmpl")
	viewInfo = {"name":viewName,"items":{},"existingItems":[],"absentItems":[]}
	for itemType in fileDic:
		item = {"type":itemType}
		item["file"] = fileDic[itemType]
		item["shortFileName"] = itemType + "/" + viewName + "." + itemType
		exists = os.path.exists(fileDic[itemType])
		item["exists"] = exists
		if exists:
			viewInfo["existingItems"].append(item)
		else:
			viewInfo["absentItems"].append(item)			
		viewInfo["items"][itemType] = item

	return viewInfo

# --------- /Module Functions: find views --------- #

# --------- Module Functions: find view base dir --------- #
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
# --------- /Module Functions: find view base dir --------- #




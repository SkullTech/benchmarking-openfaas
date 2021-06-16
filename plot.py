# for plotting metrics
import sys
import math
import pandas as pd
import matplotlib.pyplot as plt
import os
import shutil
import numpy as np

from collections import Counter
import datetime
from matplotlib.ticker import FormatStrFormatter
from itertools import cycle

def fts(x):
	return datetime.datetime.fromtimestamp(x)

class Bucket:
	def __init__(self, _min, _max, _bucket):
		self.bin_size = (_max - _min) // _bucket

		self.buckets = []
		for i in range(_min, _max, _bucket):
			self.buckets.append({
				"min": i,
				"max": i + _bucket,
				"data": []
				})

	def print(self):
		print(self.buckets)

	def add(self, secs, row):
		for i in self.buckets:
			if secs >= i["min"] and secs < i["max"]:
				i["data"].append(row)

	def get_data_list(self, colname, value):
		data_list = []
		for b in self.buckets:
			for d in b["data"]: 
				if d[colname] == value:
					data_list.append(b["min"])
		return data_list

	def get_data_list_avg(self, colname, value):
		data_list = []
		for b in self.buckets:
			for d in b["data"]: 
				if d[colname] == value:
					data_list.append(b["min"])
		return data_list

	def get_latency_data(self, colname):
		data = {'x': [], 'y': []}

		for b in self.buckets:
			data['x'].append((b["min"] + b["max"]) / 2)

			_sum, j = 0, 0
			for d in b["data"]:
				if d["statusCode"] == 200:
					_sum += float(d[colname])
					j += 1
			data['y'].append(_sum / j if j != 0 else 0)
		return data

	def get_status_data(self, colname):
		data1 = {'x': [], 'y': []}
		data2 = {'x': [], 'y': []}

		for b in self.buckets:
			data1['x'].append((b["min"] + b["max"]) / 2)
			data2['x'].append((b["min"] + b["max"]) / 2)

			data1['y'].append(len(list(filter(lambda x: x[colname]==200, b["data"]))))
			data2['y'].append(len(list(filter(lambda x: x[colname]!=200, b["data"]))))
		return data1, data2

	def get_heat_data(self):
		hdata = {}

		host_list = [h for h in list(set(self.df["hostId"])) if not pd.isna(h)]

		for host in host_list:
			hdata[host] = {'x': [], 'y': []}

			for b in self.buckets:
				hdata[host]['x'].append((b["min"] + b["max"]) / 2)
				hdata[host]['y'].append([])

		for host in host_list:
			contain = {}
			for b in self.buckets:
				for d in b["data"]:
					try:
						exec_start = (fts(d['executionStartTime']) - fts(self.request_start_time)).total_seconds()
						exec_end = (fts(d['executionEndTime']) - fts(self.request_start_time)).total_seconds()

						for e, j in enumerate(hdata[host]['x']):
							if j >= exec_start and j <= exec_end:
								if str(d["hostId"]) == str(host):
									hdata[host]['y'][e].append(d["containerId"])
					except Exception as e:
						# print(e)
						continue
		for host in hdata:
			yvals = []
			for j in range(len(hdata[host]['y'])):
				yvals.append(len([k for k in list(set(hdata[host]['y'][j])) if k != []]))
			hdata[host]['y'] = yvals
		return hdata

	def get_container_heat(self):
		hdata = {}

		contain_list = [h for h in list(set(self.df["containerId"])) if not pd.isna(h)]
		for cont in contain_list:
			hdata[cont] = {'x': [], 'y': []}
			contain = {}
			for b in self.buckets:
				hdata[cont]['x'].append((b["min"] + b["max"]) / 2)

				l = []
				for d in b["data"]:
					if str(d["containerId"]) == str(cont):
						l.append(d["requestId"])
				hdata[cont]['y'].append(len(set(l)))
		return hdata

	def get_repliacs_data(self, name):
		hdata = {'x': [], 'y': []}

		for b in self.buckets:
			hdata['x'].append((b["min"] + b["max"]) / 2)
			
			val = 0
			j = 0
			for d in b["data"]:
				val += d["replicas"]
				j += 1
			if j==0:
				hdata['y'].append(0)
			else:
				hdata['y'].append(val//j)

		return hdata

	def get_fn_invocation_rate(self, name):
		hdata = {'x': [], 'y': []}

		for b in self.buckets:
			hdata['x'].append((b["min"] + b["max"]) / 2)
			
			val = 0
			j = 0
			for d in b["data"]:
				time = d["functionInvocationRate"]
				try:
					if time.endswith("m"):
						time = float(time[:-1]) * 0.001
					elif time.endswith("n"):
						time = float(time[:-1]) * 0.000000001
					else:
						time = float(time)

					val += time
					j += 1
				except Exception as e:
					# print(e)
					continue

			if j==0:
				hdata['y'].append(0)
			else:
				hdata['y'].append(val/j)

		return hdata

	def get_requests_data(self):
		data = {'x': [], 'y': []}

		for b in self.buckets:
			data['x'].append((b["min"] + b["max"]) / 2)
			data['y'].append(len(b["data"]))
		return data

	def plot_latency_graphs(self, folder, name):
		# plt.figure(figsize=(15,8))
		fig, ax = plt.subplots(2, 1, figsize=(16,11), gridspec_kw={'height_ratios': [2, 1]})

		for g in ["executionLatency", "requestResponseLatency", "schedulingLatency"]:
			print("[*] {}".format(g))
			try:
				data = self.get_latency_data(g)
			except Exception as e:
				print(e)
				continue
			ax[0].plot(data['x'], data['y'], label='{}'.format(g), marker='.')

		ax[0].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[0].set_ylabel('Latency (in seconds)')
		ax[0].legend(loc='best')

		ax[0].xaxis.set_major_formatter(FormatStrFormatter('%d sec'))
		ax[0].yaxis.set_major_formatter(FormatStrFormatter('%d sec'))
		ax[0].set_title('Latency Plots')

		data = self.get_requests_data()
		ax[1].plot(data['x'], data['y'], marker='.')
		ax[1].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[1].set_ylabel('Number of requests')
		ax[1].set_title('Requests per second')
		ax[1].xaxis.set_major_formatter(FormatStrFormatter('%d sec'))

		plt.savefig(os.path.join(folder, '{}.png'.format(name.lower().replace(" ","_"))))

	def plot_status_graphs(self, folder, name):
		# plt.figure(figsize=(15,8))
		fig, ax = plt.subplots(2, 1, figsize=(16,11), gridspec_kw={'height_ratios': [2, 1]})

		g = "statusCode"
		print("[*] {}".format(g))

		data1, data2 = self.get_status_data(g)
		ax[0].plot(data1['x'], data1['y'], label='{}'.format("Successful Requests"), marker='.')
		ax[0].plot(data2['x'], data2['y'], label='{}'.format("Failed Requests"), marker='.')

		ax[0].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[0].set_ylabel('Number of requests')
		ax[0].legend(loc='best')

		ax[0].xaxis.set_major_formatter(FormatStrFormatter('%d sec'))
		ax[0].set_yticks(range(min(min(data1['y']), min(data2['y'])), math.ceil(max(max(data1['y']), max(data2['y'])))+1+10))

		ax[0].set_title('Successful and Failed Requests Plot')

		data = self.get_requests_data()
		ax[1].plot(data['x'], data['y'], marker='.')
		ax[1].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[1].set_ylabel('Number of requests')
		ax[1].set_title('Requests per second')
		ax[1].xaxis.set_major_formatter(FormatStrFormatter('%d sec'))

		plt.savefig(os.path.join(folder, '{}.png'.format(name.lower().replace(" ","_"))))

	def plot_replicas(self, folder, name):
		# plt.figure(figsize=(15,8))
		fig, ax = plt.subplots(2, 1, figsize=(16,11), gridspec_kw={'height_ratios': [2, 1]})

		g = "replicas"
		if g not in list(self.df.columns):
			return 
		print("[*] {}".format(g))

		data = self.get_repliacs_data(g)

		ax[0].plot(data['x'], data['y'], label='{}'.format("Replicas"), marker='.')

		ax[0].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[0].set_ylabel('Replicas')
		ax[0].legend(loc='best')

		ax[0].xaxis.set_major_formatter(FormatStrFormatter('%d sec'))
		ax[0].set_yticks(range(min(data['y']), math.ceil(max(data['y']))+1+5))
		ax[0].set_title('Kube Metric: running pod replicas per sec')

		data = self.get_requests_data()
		ax[1].plot(data['x'], data['y'], marker='.')
		ax[1].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[1].set_ylabel('Number of requests')
		ax[1].set_title('Requests per second')
		ax[1].xaxis.set_major_formatter(FormatStrFormatter('%d sec'))

		plt.savefig(os.path.join(folder, '{}.png'.format(name.lower().replace(" ","_"))))

	def plot_heat_graphs(self, folder, name):
		# plt.figure(figsize=(15,8))
		fig, ax = plt.subplots(2, 1, figsize=(16,11), gridspec_kw={'height_ratios': [2, 1]})

		print("[*] containers per host")
		try:
			hdata = self.get_heat_data()
		except:
			return

		res = [j for i in hdata for j in hdata[i]['y']]

		for e, host in enumerate(hdata):
			ax[0].plot(hdata[host]['x'], hdata[host]['y'], label='host-{}: {}'.format(e, host), marker='.')

		ax[0].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[0].set_ylabel('Running containers')

		ax[0].legend(loc='best')
		ax[0].set_yticks(range(int(min(res)), math.ceil(max(res))+1))
		ax[0].set_title('Running containers per host heat plot')

		data = self.get_requests_data()
		ax[1].plot(data['x'], data['y'], marker='.')
		ax[1].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[1].set_ylabel('Number of requests')
		ax[1].set_title('Requests per second')
		ax[1].xaxis.set_major_formatter(FormatStrFormatter('%d sec'))

		plt.savefig(os.path.join(folder, '{}.png'.format(name.lower().replace(" ","_"))))

	def plot_container_heat_graphs(self, folder, name):
		# plt.figure(figsize=(15,8))
		fig, ax = plt.subplots(2, 1, figsize=(16,11), gridspec_kw={'height_ratios': [2, 1]})

		print("[*] requests per container")
		try:
			hdata = self.get_container_heat()
		except:
			return

		res = [j for i in hdata for j in hdata[i]['y']]

		for e, host in enumerate(hdata):
			ax[0].plot(hdata[host]['x'], hdata[host]['y'], label='container-{}: {}'.format(e, host), marker='.')

		ax[0].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[0].set_ylabel('Requests per container')

		ax[0].legend(loc='best')
		ax[0].set_yticks(range(int(min(res)), math.ceil(max(res))+1))
		ax[0].set_title('Requests per container heat plot')

		data = self.get_requests_data()
		ax[1].plot(data['x'], data['y'], marker='.')
		ax[1].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[1].set_ylabel('Number of requests')
		ax[1].set_title('Requests per second')
		ax[1].xaxis.set_major_formatter(FormatStrFormatter('%d sec'))

		plt.savefig(os.path.join(folder, '{}.png'.format(name.lower().replace(" ","_"))))


	def plot_fn_invocation_rate(self, folder, name):
		# plt.figure(figsize=(15,8))
		fig, ax = plt.subplots(2, 1, figsize=(16,11), gridspec_kw={'height_ratios': [2, 1]})

		g = "functionInvocationRate"
		if g not in list(self.df.columns):
			return 

		print("[*] {}".format(g))
		data = self.get_fn_invocation_rate(g)

		ax[0].plot(data['x'], data['y'], label='{}'.format("Function Invocation Rate (in secs)"), marker='.')

		ax[0].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[0].set_ylabel('Function inovcation rate')
		ax[0].legend(loc='best')
		ax[0].xaxis.set_major_formatter(FormatStrFormatter('%d sec'))
		ax[0].yaxis.set_major_formatter(FormatStrFormatter('%d sec'))
		# ax[0].yticks(range(int(min(data['y'])), math.ceil(int(max(data['y']))+1+5)))
		ax[0].set_title('Function Invocation Rate')

		data = self.get_requests_data()
		ax[1].plot(data['x'], data['y'], marker='.')
		ax[1].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[1].set_ylabel('Number of requests')
		ax[1].set_title('Requests per second')
		ax[1].xaxis.set_major_formatter(FormatStrFormatter('%d sec'))

		plt.savefig(os.path.join(folder, '{}.png'.format(name.lower().replace(" ","_"))))

	def get_memory_usage(self, name):
		if name not in list(self.df.columns):
			return {}
		data = {'x': [], 'y': []}

		for b in self.buckets:
			data['x'].append((b["min"] + b["max"]) / 2)
			
			val = 0
			j = 0
			for d in b["data"]:
				v = d[name]

				if not pd.isna(v):
					if v.endswith("Ki"):
						v = (float(v[:-2]) / 1024)
					elif v.endswith("Mi"):
						v = (float(v[:-2]))
					else:
						v = float(v) / (1024*1024)

					val += v
					j += 1
			if j==0:
				data['y'].append(0)
			else:
				data['y'].append(val/j)
		return data

	def plot_memory_usage(self, folder, name):
		# plt.figure(figsize=(15,8))
		fig, ax = plt.subplots(2, 1, figsize=(16,11), gridspec_kw={'height_ratios': [2, 1]})

		g = "MemoryUsage"
		print("[*] {}".format(g))

		nodes = []
		for col in self.df.columns:
			if col.endswith("MemoryUsage"):
				nodes.append(col)

		for n in nodes:
			data = self.get_memory_usage(n)
			if data == {}:
				continue
			ax[0].plot(data['x'], data['y'], label='{}'.format(n[:2]), marker='.')

		ax[0].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[0].set_ylabel('Memory Usage (in Kb)')
		ax[0].legend(loc='best')

		ax[0].xaxis.set_major_formatter(FormatStrFormatter('%d sec'))
		# ax[0].yaxis.set_major_formatter(FormatStrFormatter('%d Mb'))
		# ax[0].set_yticks(range(int(min(data['y'])), math.ceil(int(max(data['y']))+1)))
		ax[0].set_title('Memory Usage per host-node')
 
		data = self.get_requests_data()
		ax[1].plot(data['x'], data['y'], marker='.')
		ax[1].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[1].set_ylabel('Number of requests')
		ax[1].set_title('Requests per second')
		ax[1].xaxis.set_major_formatter(FormatStrFormatter('%d sec'))

		plt.savefig(os.path.join(folder, '{}.png'.format(name.lower().replace(" ","_"))))

	def get_cpu_usage(self, name):
		if name not in list(self.df.columns):
			return {}

		data = {'x': [], 'y': []}

		for b in self.buckets:
			data['x'].append((b["min"] + b["max"]) / 2)
			
			val = 0
			j = 0
			for d in b["data"]:
				v = d[name]

				if not pd.isna(v):
					if v.endswith("n"):
						v = (float(v[:-1])) / 1000000000
					elif v.endswith("u"):
						v = (float(v[:-1])) / 1000000
					else:
						v = float(v)
						# print(v)

					val += v
					j += 1

			if j==0:
				data['y'].append(0)
			else:
				data['y'].append(val/j)
		return data

	def plot_cpu_usage(self, folder, name):
		# plt.figure(figsize=(15,8))
		fig, ax = plt.subplots(2, 1, figsize=(16,11), gridspec_kw={'height_ratios': [2, 1]})

		g = "CpuUsage"
		print("[*] {}".format(g))

		nodes = []
		for col in self.df.columns:
			if col.endswith("CpuUsage"):
				nodes.append(col)

		for n in nodes:
			data = self.get_cpu_usage(n)
			if data == {}:
				continue
			# print(data)
			ax[0].plot(data['x'], data['y'], label='{}'.format(n[:2]), marker='.')

		ax[0].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[0].set_ylabel('CPU Usage')
		ax[0].legend(loc='best')

		ax[0].xaxis.set_major_formatter(FormatStrFormatter('%d sec'))
		# ax[0].yaxis.set_major_formatter(FormatStrFormatter('%d ms'))
		ax[0].set_yticks([round(x,5) for x in np.arange(0, 4, 0.1)])
		ax[0].set_title('CPU Usage per host-node')

		data = self.get_requests_data()
		ax[1].plot(data['x'], data['y'], marker='.')
		ax[1].set_xlabel('Time in seconds (start-time: {})'.format(str(fts(self.request_start_time))))
		ax[1].set_ylabel('Number of requests')
		ax[1].set_title('Requests per second')
		ax[1].xaxis.set_major_formatter(FormatStrFormatter('%d sec'))

		plt.savefig(os.path.join(folder, '{}.png'.format(name.lower().replace(" ","_"))))


if __name__ == '__main__':

	file = sys.argv[1]
	dirpath = sys.argv[2]
	df = pd.read_csv(file)


	reqtime = sorted(list(Counter(df['requestTime'])))
	time = [((fts(i)-fts(reqtime[0])).total_seconds(), i) for i in list(reqtime)]

	request_start_time = reqtime[0]
	request_end_time = reqtime[-1]

	START_TIME = 0
	END_TIME = int((fts(request_end_time) - fts(request_start_time)).total_seconds())+1
	INTERVAL = 10

	buck = Bucket(START_TIME, END_TIME, INTERVAL) 
	buck.df = df

	buck.request_start_time = request_start_time

	for i, row in df.iterrows():
		secs = (fts(row['requestTime']) - fts(request_start_time)).total_seconds()
		buck.add(secs, row)

	# dirpath = "./" + (file.split("/")[-1]).split(".")[0]

	if os.path.exists(dirpath) and os.path.isdir(dirpath):
		shutil.rmtree(dirpath)
	os.mkdir(dirpath)

	buck.plot_latency_graphs(dirpath, "Latency Plots")
	buck.plot_status_graphs(dirpath, "Status Code")
	buck.plot_heat_graphs(dirpath, "Containers Per Hosts")
	buck.plot_container_heat_graphs(dirpath, "Requests Per Container")
	buck.plot_replicas(dirpath, "Pod Replicas")
	buck.plot_fn_invocation_rate(dirpath, "Function Invocation Rate")
	buck.plot_memory_usage(dirpath, "Nodes Memory Usage")
	buck.plot_cpu_usage(dirpath, "Nodes CPU Usage")
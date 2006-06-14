
import gtk
import gtk.glade

import matplotlib
matplotlib.use('GTK')

from matplotlib.figure import Figure
from matplotlib.axes import Subplot
from matplotlib.backends.backend_gtk import FigureCanvasGTK, NavigationToolbar

from matplotlib.numerix import arange, sin, pi

class vmmDetails:
    def __init__(self, config, connection, vm, vmuuid):
        self.window = gtk.glade.XML(config.get_glade_file(), "vmm-details")
        self.config = config
        self.connection = connection
        self.vm = vm
        self.vmuuid = vmuuid
        self.lastStatus = None

        topwin = self.window.get_widget("vmm-details")
        topwin.hide()
        topwin.set_title(vm.name() + " " + topwin.get_title())

        self.window.get_widget("overview-name").set_text(vm.name())
        self.window.get_widget("overview-uuid").set_text(vmuuid)

        self.window.get_widget("control-run").set_icon_widget(gtk.Image())
        self.window.get_widget("control-run").get_icon_widget().set_from_file(config.get_icon_dir() + "/icon_run.png")

        self.window.get_widget("control-pause").set_icon_widget(gtk.Image())
        self.window.get_widget("control-pause").get_icon_widget().set_from_file(config.get_icon_dir() + "/icon_pause.png")

        self.window.get_widget("control-shutdown").set_icon_widget(gtk.Image())
        #self.window.get_widget("control-shutdown").get_icon_widget().set_from_file(config.get_icon_dir() + "/icon_run.png")

        self.window.get_widget("control-terminal").set_icon_widget(gtk.Image())
        self.window.get_widget("control-terminal").get_icon_widget().set_from_file(config.get_icon_dir() + "/icon_launch_term.png")

        self.window.get_widget("control-snapshot").set_icon_widget(gtk.Image())
        self.window.get_widget("control-snapshot").get_icon_widget().set_from_file(config.get_icon_dir() + "/icon_snapshot.png")

        self.window.get_widget("hw-panel").set_show_tabs(False)

        hwListModel = gtk.ListStore(int, str, gtk.gdk.Pixbuf)
        self.window.get_widget("hw-list").set_model(hwListModel)

        hwListModel.append([0, "Processor", gtk.gdk.pixbuf_new_from_file(config.get_icon_dir() + "/icon_cpu.png")])
        #hwListModel.append([1, "Memory", gtk.gdk.pixbuf_new_from_file(config.get_icon_dir() + "/icon_ram.png")])
        hwListModel.append([1, "Memory", gtk.gdk.pixbuf_new_from_file(config.get_icon_dir() + "/icon_cpu.png")])
        hwListModel.append([2, "Disk", gtk.gdk.pixbuf_new_from_file(config.get_icon_dir() + "/icon_hdd.png")])
        hwListModel.append([3, "Network", gtk.gdk.pixbuf_new_from_file(config.get_icon_dir() + "/icon_ethernet.png")])
        hwListModel.append([4, "Add hardware", gtk.gdk.pixbuf_new_from_file(config.get_icon_dir() + "/icon_addnew.png")])

        self.window.get_widget("hw-list").get_selection().connect("changed", self.hw_selected)


        hwCol = gtk.TreeViewColumn("Hardware")
        hw_txt = gtk.CellRendererText()
        hw_img = gtk.CellRendererPixbuf()
        hwCol.pack_start(hw_txt, True)
        hwCol.pack_start(hw_img, False)
        hwCol.add_attribute(hw_txt, 'text', 1)
        hwCol.add_attribute(hw_img, 'pixbuf', 2)

        self.window.get_widget("hw-list").append_column(hwCol)


        self.cpu_usage_figure = Figure()
        self.cpu_usage_graph = self.cpu_usage_figure.add_subplot(111)
        self.cpu_usage_graph.set_autoscale_on(False)
        self.cpu_usage_line = None
        self.cpu_usage_line_avg = None
        self.cpu_usage_canvas = FigureCanvasGTK(self.cpu_usage_figure)
        self.cpu_usage_canvas.show()
        self.window.get_widget("graph-table").attach(self.cpu_usage_canvas, 1, 2, 0, 1)

        self.memory_usage_figure = Figure()
        self.memory_usage_graph = self.memory_usage_figure.add_subplot(111)
        self.memory_usage_graph.set_autoscale_on(False)
        self.memory_usage_line = None
        self.memory_usage_canvas = FigureCanvasGTK(self.memory_usage_figure)
        self.memory_usage_canvas.show()
        self.window.get_widget("graph-table").attach(self.memory_usage_canvas, 1, 2, 1, 2)

        self.network_traffic_figure = Figure()
        self.network_traffic_graph = self.network_traffic_figure.add_subplot(111)
        self.network_traffic_graph.set_autoscale_on(False)
        self.network_traffic_line = None
        self.network_traffic_canvas = FigureCanvasGTK(self.network_traffic_figure)
        self.network_traffic_canvas.show()
        self.window.get_widget("graph-table").attach(self.network_traffic_canvas, 1, 2, 3, 4)

        self.config.on_stats_history_length_changed(self.change_graph_ranges)

        self.window.signal_autoconnect({
            "on_close_details_clicked": self.close,
            "on_vmm_details_delete_event": self.close,

            "on_control_run_clicked": self.control_vm_run,
            "on_control_shutdown_clicked": self.control_vm_shutdown,
            "on_control_pause_toggled": self.control_vm_pause,

            "on_control_terminal_clicked": self.control_vm_terminal,
            "on_control_snapshot_clicked": self.control_vm_snapshot,
            })

        self.connection.connect("vm-updated", self.refresh_overview)
        self.change_graph_ranges()
        self.refresh_overview(self.connection, vmuuid)
        self.hw_selected()

    def show(self):
        dialog = self.window.get_widget("vmm-details")
        dialog.show_all()
        dialog.present()

    def close(self,ignore1=None,ignore2=None):
        self.window.get_widget("vmm-details").hide()
        return 1

    def hw_selected(self, src=None):
        vmlist = self.window.get_widget("hw-list")
        selection = vmlist.get_selection()
        active = selection.get_selected()
        if active[1] != None:
            self.window.get_widget("hw-panel").set_sensitive(True)
            self.window.get_widget("hw-panel").set_current_page(active[0].get_value(active[1], 0))
        else:
            self.window.get_widget("hw-panel").set_sensitive(False)

    def control_vm_run(self, src):
        return 0

    def control_vm_shutdown(self, src):
        if not(self.connection.get_stats().run_status(self.vmuuid) in [ "shutdown", "shutoff" ]):
            self.vm.shutdown()
        else:
            print "Shutdown requested, but machine is already shutting down / shutoff"

    def control_vm_pause(self, src):
        if self.connection.get_stats().run_status(self.vmuuid) in [ "shutdown", "shutoff" ]:
            print "Pause/resume requested, but machine is shutdown / shutoff"
        else:
            if self.connection.get_stats().run_status(self.vmuuid) in [ "paused" ]:
                if not src.get_active():
                    self.vm.resume()
                else:
                    print "Pause requested, but machine is already paused"
            else:
                if src.get_active():
                    self.vm.suspend()
                else:
                    print "Resume requested, but machine is already running"


    def control_vm_terminal(self, src):
        return 0

    def control_vm_snapshot(self, src):
        return 0

    def change_graph_ranges(self, ignore1=None,ignore2=None,ignore3=None,ignore4=None):
        self.cpu_usage_graph.clear()
        #self.cpu_usage_graph.set_xlabel('History')
        #self.cpu_usage_graph.set_ylabel('% utilization')
        self.cpu_usage_graph.grid(True)
        self.cpu_usage_line = None

        self.memory_usage_graph.clear()
        #self.memory_usage_graph.set_xlabel('History')
        #self.memory_usage_graph.set_ylabel('% utilization')
        self.memory_usage_graph.grid(True)
        self.memory_usage_line = None

        self.network_traffic_graph.clear()
        #self.network_traffic_graph.set_xlabel('History')
        #self.network_traffic_graph.set_ylabel('% utilization')
        self.network_traffic_graph.grid(True)
        self.network_traffic_line = None

    def update_widget_states(self, status):
        if self.lastStatus == status:
            return

        if status == "shutoff":
            self.window.get_widget("control-run").set_sensitive(True)
        else:
            self.window.get_widget("control-run").set_sensitive(False)

        if status in [ "shutoff", "shutdown" ]:
            self.window.get_widget("control-pause").set_sensitive(False)
            self.window.get_widget("control-shutdown").set_sensitive(False)
            self.window.get_widget("control-terminal").set_sensitive(False)
            self.window.get_widget("control-snapshot").set_sensitive(False)
        else:
            self.window.get_widget("control-pause").set_sensitive(True)
            self.window.get_widget("control-shutdown").set_sensitive(True)
            self.window.get_widget("control-terminal").set_sensitive(True)
            self.window.get_widget("control-snapshot").set_sensitive(True)
            if status == "paused":
                self.window.get_widget("control-pause").set_active(True)
            else:
                self.window.get_widget("control-pause").set_active(False)

        self.lastStatus = status

    def refresh_overview(self, connection, vmuuid):
        if not(vmuuid == self.vmuuid):
            return

        status = self.connection.get_stats().run_status(vmuuid)
        self.update_widget_states(status)

        self.window.get_widget("overview-status-text").set_text(status)
        self.window.get_widget("overview-status-icon").set_from_pixbuf(self.connection.get_stats().run_status_icon(vmuuid))
        self.window.get_widget("overview-cpu-usage-text").set_text("%d %%" % self.connection.get_stats().cpu_time_percentage(vmuuid))
        self.window.get_widget("overview-memory-usage-text").set_text("%d MB of %d MB" % (self.connection.get_stats().current_memory(vmuuid)/1024, self.connection.get_stats().host_memory_size()/1024))

        history_len = self.config.get_stats_history_length()
        cpu_vector = self.connection.get_stats().cpu_time_vector(vmuuid)
        cpu_vector.reverse()
        cpu_vector_avg = self.connection.get_stats().cpu_time_moving_avg_vector(vmuuid)
        cpu_vector_avg.reverse()
        if self.cpu_usage_line == None:
            self.cpu_usage_line = self.cpu_usage_graph.plot(cpu_vector)
            self.cpu_usage_line_avg = self.cpu_usage_graph.plot(cpu_vector_avg)
            self.cpu_usage_graph.set_xlim(0, history_len)
            self.cpu_usage_graph.set_ylim(0, 100)
        else:
            self.cpu_usage_line[0].set_ydata(cpu_vector)
            self.cpu_usage_line_avg[0].set_ydata(cpu_vector_avg)
            self.cpu_usage_graph.set_xlim(0, history_len)
            self.cpu_usage_graph.set_ylim(0, 100)
        self.cpu_usage_graph.set_yticklabels(["0","","","","","100"])
        self.cpu_usage_graph.set_xticklabels([])
        self.cpu_usage_canvas.draw()

        history_len = self.config.get_stats_history_length()
        memory_vector = self.connection.get_stats().current_memory_vector(vmuuid)
        memory_vector.reverse()
        if self.memory_usage_line == None:
            self.memory_usage_line = self.memory_usage_graph.plot(memory_vector)
            self.memory_usage_graph.set_xlim(0, history_len)
            self.memory_usage_graph.set_ylim(0, 100)
        else:
            self.memory_usage_line[0].set_ydata(memory_vector)
            self.memory_usage_graph.set_xlim(0, history_len)
            self.memory_usage_graph.set_ylim(0, 100)
        self.memory_usage_graph.set_yticklabels(["0","","","","","100"])
        self.memory_usage_graph.set_xticklabels([])
        self.memory_usage_canvas.draw()

        history_len = self.config.get_stats_history_length()
        #if self.network_traffic_line == None:
            #self.network_traffic_line = self.network_traffic_graph.plot(self.connection.get_stats().network_traffic_vector(vmuuid))
        #else:
            #self.network_traffic_line[0].set_ydata(self.connection.get_stats().network_traffic_vector(vmuuid))
        self.network_traffic_graph.set_xlim(0, history_len)
        self.network_traffic_graph.set_ylim(0, 100)
        self.network_traffic_graph.set_yticklabels(["0","","","","","100"])
        self.network_traffic_graph.set_xticklabels([])
        self.network_traffic_canvas.draw()


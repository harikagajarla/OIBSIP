import queue, tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from .network import ChatClient

class ChatApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("OIBSIP Advanced Chat"); self.geometry("860x560"); self.client=ChatClient(); self.username=None; self.room=None
        self.status=tk.StringVar(value="Disconnected"); self.notice=tk.StringVar(); self.protocol("WM_DELETE_WINDOW", self.quit_app); self.login_screen(); self.after(100, self.process_events)
    def clear(self):
        for item in self.winfo_children(): item.destroy()
    def connect(self):
        try: self.client.connect(self.host.get().strip(), self.port.get().strip()); self.status.set("Connected")
        except OSError as exc: messagebox.showerror("Connection failed", str(exc))
    def login_screen(self):
        self.clear(); frame=ttk.Frame(self,padding=30); frame.pack(expand=True); ttk.Label(frame,text="Advanced Chat Application",font=("Segoe UI",20,"bold")).grid(columnspan=2,pady=12)
        self.host=tk.StringVar(value="127.0.0.1"); self.port=tk.StringVar(value="5000"); self.user=tk.StringVar(); self.password=tk.StringVar()
        for row,label,var,show in [(1,"Server",self.host,None),(2,"Port",self.port,None),(3,"Username",self.user,None),(4,"Password",self.password,"*")]:
            ttk.Label(frame,text=label).grid(row=row,column=0,sticky="e",padx=6,pady=5); ttk.Entry(frame,textvariable=var,show=show,width=30).grid(row=row,column=1,pady=5)
        ttk.Button(frame,text="Register",command=lambda:self.auth("register")).grid(row=5,column=0,pady=12); ttk.Button(frame,text="Login",command=lambda:self.auth("login")).grid(row=5,column=1,pady=12)
        ttk.Label(frame,textvariable=self.status).grid(row=6,columnspan=2)
    def auth(self, action):
        try:
            if not self.client.connected: self.connect()
            self.client.send(action,username=self.user.get(),password=self.password.get())
        except (OSError, ConnectionError) as exc: messagebox.showerror("Connection failed",str(exc))
    def chat_screen(self, rooms):
        self.clear(); root=ttk.Frame(self,padding=10); root.pack(fill="both",expand=True); left=ttk.Frame(root); left.pack(side="left",fill="y"); main=ttk.Frame(root); main.pack(side="left",fill="both",expand=True,padx=(10,0))
        ttk.Label(left,text=f"Signed in as {self.username}",font=("Segoe UI",11,"bold")).pack(); self.room_list=tk.Listbox(left,width=22); self.room_list.pack(fill="y",expand=True,pady=8); self.room_list.bind("<<ListboxSelect>>",self.join_selected)
        ttk.Button(left,text="Create room",command=self.create_room).pack(fill="x"); ttk.Button(left,text="Refresh rooms",command=lambda:self.client.send("rooms")).pack(fill="x",pady=3); ttk.Button(left,text="Logout",command=self.logout).pack(fill="x")
        self.chat=tk.Text(main,state="disabled",wrap="word"); self.chat.pack(fill="both",expand=True); self.entry=tk.StringVar(); ttk.Entry(main,textvariable=self.entry).pack(fill="x",side="left",expand=True,pady=8); ttk.Button(main,text="Send",command=self.send_chat).pack(side="left",padx=5); ttk.Label(main,textvariable=self.notice,foreground="#b45309").pack(anchor="w"); ttk.Label(main,textvariable=self.status).pack(anchor="w")
        self.show_rooms(rooms)
    def show_rooms(self, rooms):
        self.rooms=rooms; self.room_list.delete(0,"end")
        for room in rooms: self.room_list.insert("end",room["name"])
    def join_selected(self,_=None):
        selection=self.room_list.curselection()
        if selection: self.client.send("join_room",room_id=self.rooms[selection[0]]["id"])
    def create_room(self):
        name=simpledialog.askstring("Create room","Room name:",parent=self)
        if name: self.client.send("create_room",name=name)
    def send_chat(self):
        try: self.client.send("chat",body=self.entry.get()); self.entry.set("")
        except ConnectionError as exc: self.status.set(str(exc))
    def display(self,m):
        self.chat.configure(state="normal"); self.chat.insert("end",f"[{m['timestamp']}] {m['sender']}: {m['body']}\n"); self.chat.see("end"); self.chat.configure(state="disabled")
    def process_events(self):
        try:
            while True:
                event=self.client.events.get_nowait()
                if event.get("event")=="chat":
                    if event["room_id"]==self.room: self.display(event)
                    if not self.focus_displayof(): self.notice.set("New message received while this window was not focused.")
                elif event.get("event")=="connection": self.status.set(event["message"])
                elif event.get("event")=="response":
                    if not event["ok"]: self.status.set(event["message"]); continue
                    if event.get("username"): self.username=event["username"]; self.chat_screen(event.get("rooms",[]))
                    if "rooms" in event: self.show_rooms(event["rooms"])
                    if event.get("room"): self.room=event["room"]["id"]; self.title(f"OIBSIP Advanced Chat — {event['room']['name']}"); self.chat.configure(state="normal"); self.chat.delete("1.0","end"); self.chat.configure(state="disabled"); [self.display(x) for x in event.get("history",[])]
                    if event.get("room_id"): self.client.send("rooms")
                    self.status.set(event["message"])
        except queue.Empty: pass
        self.after(100,self.process_events)
    def logout(self):
        if self.client.connected: self.client.send("logout")
        self.client.close(); self.username=None; self.login_screen()
    def quit_app(self): self.client.close(); self.destroy()

if __name__=="__main__": ChatApp().mainloop()

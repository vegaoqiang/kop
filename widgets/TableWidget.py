
from textual.app import App, ComposeResult
from textual.widgets import Footer, ListItem, ListView, Button, Static
from textual.containers import Horizontal


class NameCol(Static):
    
    DEFAULT_CSS = """
      NameCol {
        height: 1;
        width: 20%;
      }
    """


class NamespaceCol(Static):
     
     DEFAULT_CSS = """
        NamespaceCol {
          height: 1;
          width: 10%;
        }
      """
     

class ContainersCol(Static):
     
     DEFAULT_CSS = """
        ContainersCol {
          height: 1;
          width: 10%;
        }
      """

class RestartsCol(Static):
     
     DEFAULT_CSS = """
        RestartsCol {
          height: 1;
          width: 5%;
        }
      """

class ControlledByCol(Static):
     
     DEFAULT_CSS = """
        ControlledByCol {
          height: 1;
          width: 10%;
        }
      """
     
class NodeCol(Static):
     
     DEFAULT_CSS = """
        NodeCol {
          height: 1;
          width: 10%;
        }
      """

class QoSCol(Static):
     
     DEFAULT_CSS = """
        QoSCol {
          height: 1;
          width: 5%;
        }
      """

class AgeCol(Static):
     
     DEFAULT_CSS = """
        AgeCol {
          height: 1;
          width: 5%;
        }
      """

class StatusCol(Static):
     
     DEFAULT_CSS = """
        StatusCol {
          height: 1;
          width: 5%;
        }
      """
    
class ActiveCol(Static):
     
     DEFAULT_CSS = """
        ActiveCol {
          height: 1;
          width: 20%;
        }
      """
    

class ActiveGroup(Horizontal):
     
     DEFAULT_CSS = """
        .t {
          width: 4;
          min-width: 4;
          margin: 0 1;
        }
      """
     
     def compose(self) -> ComposeResult:
          yield Button(">_", classes='t', compact=True, tooltip="shell", variant="success")
          yield Button("log", classes='t', compact=True, tooltip="shell", variant="success")


class TableHeader(ListItem):
    DEFAULT_CSS = """
        TableHeader {
          height: 1;
          width: 1fr;
          background: steelblue;
        }
    """

    def compose(self) -> ComposeResult:
          with Horizontal():
            yield  NameCol("Name")
            yield  NamespaceCol("Namespace")
            yield  ContainersCol("Containers")
            yield  RestartsCol("Restarts")
            yield  ControlledByCol("ControlledBy")
            yield  NodeCol("Node")
            yield  QoSCol("QoS")
            yield  AgeCol("Age")
            yield  StatusCol("Status")
            yield  ActiveCol("Active")
        

class TableRow(ListItem):
    can_focus = True


    DEFAULT_CSS = """
        TableRow {
          height: 1;
          width: 1fr;
          background: transparent;
        }

    """

    def __init__(self, row_data: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.row_data = row_data


    def compose(self) -> ComposeResult:
          with Horizontal():
            yield  NameCol(self.row_data["Name"])
            yield  NamespaceCol(self.row_data["Namespace"])
            yield  ContainersCol(self.row_data["Containers"])
            yield  RestartsCol(self.row_data["Restarts"])
            yield  ControlledByCol(self.row_data["ControlledBy"])
            yield  NodeCol(self.row_data["Node"])
            yield  QoSCol(self.row_data["QoS"])
            yield  AgeCol(self.row_data["Age"])
            yield  StatusCol(self.row_data["Status"])
            yield  ActiveGroup()



class Table(ListView):
    DEFAULT_CSS = """
        Table {
          height: auto;
          width: 1fr;
          & > TableRow {
              height: 1;
              overflow: hidden hidden;
              width: 1fr;
              
              &.-hovered {
                    background: $block-hover-background;
                }
                
              &.-highlight {
                  color: $block-cursor-blurred-foreground;
                  background: $block-cursor-blurred-background;
                  text-style: $block-cursor-blurred-text-style;
              }
          }
          & > TableHeader {
              height: 1;
              overflow: hidden hidden;
              width: 1fr;
          }
        }
      
    """

        
    def compose(self) -> ComposeResult:
         yield TableHeader()
         yield TableRow({
            "Name": "redis-abc",
            "Namespace": "cache",
            "Containers": "2",
            "Restarts": "1",
            "ControlledBy": "StatefulSet",
            "Node": "node-2",
            "QoS": "Burstable",
            "Age": "5h",
            "Status": "Pending",
            "Active": "No"
        })
         yield TableRow({
            "Name": "redis-abc",
            "Namespace": "cache",
            "Containers": "2",
            "Restarts": "1",
            "ControlledBy": "StatefulSet",
            "Node": "node-2",
            "QoS": "Burstable",
            "Age": "5h",
            "Status": "Pending",
            "Active": "No"
        })

         
    


class CustomApp(App):
     BINDINGS = [
          ("a", "add_row", "Add"),
      ]
     def compose(self) -> ComposeResult:
          yield Table()
          yield Footer()

     def action_add_row(self, row_data: dict|None = None) -> None:
          row_data = {
            "Name": "redis-abc",
            "Namespace": "cache",
            "Containers": "2",
            "Restarts": "1",
            "ControlledBy": "StatefulSet",
            "Node": "node-2",
            "QoS": "Burstable",
            "Age": "5h",
            "Status": "Pending",
            "Active": "No"
        }
          row  = TableRow(row_data)
          self.query_one(Table).mount(row)
          row.scroll_visible()


if __name__ == "__main__":
    app = CustomApp()
    app.run()
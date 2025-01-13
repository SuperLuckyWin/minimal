from collections import deque

class DataManager:
    def __init__(self, max_size=1000):
        self.data = {}
        self.max_size = max_size

    def update_data(self, symbol, data_type, data):
      """更新数据"""
      key = (symbol, data_type)
      if key not in self.data:
        self.data[key] = deque(maxlen=self.max_size)
      self.data[key].append(data)

    def get_data(self, symbol, data_type, limit=None):
        """获取数据"""
        key = (symbol, data_type)
        if key not in self.data:
          return []
        if limit is None:
            return list(self.data[key])
        else:
            return list(self.data[key])[-limit:]

    def clear_data(self, symbol=None, data_type=None):
        """清空数据"""
        if symbol is None and data_type is None:
            self.data.clear()
        elif symbol is not None and data_type is not None:
            key = (symbol, data_type)
            if key in self.data:
                del self.data[key]
        elif symbol is not None and data_type is None:
            keys_to_remove = [k for k in self.data.keys() if k[0] == symbol]
            for key in keys_to_remove:
                del self.data[key]
        elif symbol is None and data_type is not None:
            keys_to_remove = [k for k in self.data.keys() if k[1] == data_type]
            for key in keys_to_remove:
                del self.data[key]

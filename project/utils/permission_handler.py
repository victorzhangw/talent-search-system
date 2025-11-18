class PermissionHandler:
    _permissions = {
        'business': ['quote_manage', 'order_manage'],
        'admin': ['quote_manage', 'order_manage', 'shipment_manage', 'user_manage'],
    }

    @staticmethod
    def get_permissions(user_type):
        """獲取用戶權限"""
        permissions = PermissionHandler._permissions.get(user_type, [])
        print(f"Getting permissions for {user_type}: {permissions}")  # 添加調試輸出
        return permissions

    @staticmethod
    def has_permission(user_type, permission_code):
        """檢查是否有權限"""
        return permission_code in PermissionHandler._permissions.get(user_type, [])
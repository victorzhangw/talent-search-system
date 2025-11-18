# api/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from core.models import (
    User, TestProject, TestInvitation, TestInvitee, 
    TestProjectResult, InvitationTemplate, UserPointBalance
)

class UserSerializer(serializers.ModelSerializer):
    """用戶序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'user_type', 'phone', 'is_active', 'date_joined']
        read_only_fields = ['id', 'date_joined']

class UserRegistrationSerializer(serializers.ModelSerializer):
    """用戶註冊序列化器"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'user_type', 'phone']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("密碼不一致")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    """登入序列化器"""
    username = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('帳號或密碼錯誤')
            if not user.is_active:
                raise serializers.ValidationError('帳號已被停用')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('請提供用戶名和密碼')
        
        return attrs

class TestProjectSerializer(serializers.ModelSerializer):
    """測驗項目序列化器"""
    class Meta:
        model = TestProject
        fields = ['id', 'name', 'description', 'test_link', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class TestInviteeSerializer(serializers.ModelSerializer):
    """受測者序列化器"""
    class Meta:
        model = TestInvitee
        fields = ['id', 'name', 'email', 'phone', 'department', 'position', 'invited_count', 'created_at']
        read_only_fields = ['id', 'invited_count', 'created_at']

class TestInvitationSerializer(serializers.ModelSerializer):
    """測驗邀請序列化器"""
    invitee = TestInviteeSerializer(read_only=True)
    test_project = TestProjectSerializer(read_only=True)
    invitee_id = serializers.IntegerField(write_only=True)
    test_project_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = TestInvitation
        fields = [
            'id', 'invitation_code', 'invitee', 'test_project', 'status', 'custom_message',
            'invited_at', 'expires_at', 'started_at', 'completed_at', 'score',
            'invitee_id', 'test_project_id'
        ]
        read_only_fields = ['id', 'invitation_code', 'invited_at', 'started_at', 'completed_at', 'score']

class TestProjectResultSerializer(serializers.ModelSerializer):
    """測驗結果序列化器"""
    test_invitation = TestInvitationSerializer(read_only=True)
    
    class Meta:
        model = TestProjectResult
        fields = [
            'id', 'test_invitation', 'test_project', 'score_value', 'prediction_value',
            'category_results', 'raw_data', 'crawled_at', 'created_at'
        ]
        read_only_fields = ['id', 'crawled_at', 'created_at']

class InvitationTemplateSerializer(serializers.ModelSerializer):
    """邀請模板序列化器"""
    class Meta:
        model = InvitationTemplate
        fields = [
            'id', 'name', 'template_type', 'subject', 'message', 'is_default',
            'is_active', 'usage_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at']

class UserPointBalanceSerializer(serializers.ModelSerializer):
    """用戶點數餘額序列化器"""
    class Meta:
        model = UserPointBalance
        fields = ['id', 'user', 'balance', 'total_earned', 'total_consumed', 'last_updated']
        read_only_fields = ['id', 'user', 'last_updated']

class PasswordChangeSerializer(serializers.Serializer):
    """密碼修改序列化器"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("新密碼不一致")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("原密碼錯誤")
        return value

class StatisticsSerializer(serializers.Serializer):
    """統計數據序列化器"""
    total_invitations = serializers.IntegerField()
    total_invitees = serializers.IntegerField()
    completed_tests = serializers.IntegerField()
    pending_tests = serializers.IntegerField()
    completion_rate = serializers.FloatField()
    
    # 圖表數據
    daily_trend = serializers.DictField()
    status_distribution = serializers.DictField()
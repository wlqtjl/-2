import React, { useState } from 'react';
import { ArrowLeft, Plus, Sparkles, Brain, FileText, TrendingUp } from 'lucide-react';
import { contentAPI, courseAPI } from '../api';
import { CourseSelector, FileUploader, ProgressStatus } from '../components/ContentImport';
import LevelEditor from '../components/LevelEditor';
import { AIConfigPanel } from '../components/AIConfigPanel';

type ViewMode = 'dashboard' | 'import' | 'courses' | 'editor' | 'analytics' | 'aiconfig';

export const InstructorDashboard: React.FC = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('dashboard');
  const [selectedCourse, setSelectedCourse] = useState<any>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [courses, setCourses] = useState<any[]>([]);
  const [aiStatus, setAiStatus] = useState<any>(null);

  React.useEffect(() => {
    const loadData = async () => {
      const [courseData, statusData] = await Promise.all([
        courseAPI.getCourses(),
        contentAPI.getAIStatus().catch(() => ({ api_configured: false, coordinator_ready: false })),
      ]);
      setCourses(courseData);
      setAiStatus(statusData);
    };
    loadData();
  }, []);

  const handleImport = async (file: File, courseId: number): Promise<string> => {
    const result = await contentAPI.importContent(
      courseId,
      file,
      file.name.replace(/\.[^/.]+$/, '')
    );
    setJobId(result.job_id);
    return result.job_id;
  };

  const navigateTo = (mode: ViewMode) => {
    setViewMode(mode);
    if (mode !== 'editor') {
      setSelectedCourse(null);
    }
  };

  const stats = [
    { label: '课程总数', value: courses.length, icon: FileText, color: 'blue' },
    { label: '总关卡', value: courses.reduce((sum, c) => sum + (c.levels?.length || 0), 0), icon: Sparkles, color: 'purple' },
    { label: 'AI 状态', value: aiStatus?.api_configured ? '就绪' : '未配置', icon: Brain, color: aiStatus?.api_configured ? 'green' : 'yellow' },
  ];

  const quickActions = [
    { label: '导入内容', mode: 'import', icon: Sparkles, desc: '上传文档自动生成关卡' },
    { label: '课程管理', mode: 'courses', icon: FileText, desc: '管理现有课程和关卡' },
    { label: '数据分析', mode: 'analytics', icon: TrendingUp, desc: '查看学员学习数据' },
    { label: 'AI 配置', mode: 'aiconfig', icon: Brain, desc: '配置 AI API 密钥' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      {viewMode === 'dashboard' && (
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">讲师工作台</h1>
            <p className="text-gray-600 mt-2">管理课程内容，AI 自动生成培训关卡</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {stats.map((stat, idx) => (
              <div key={idx} className="bg-white rounded-2xl shadow-sm p-6 border border-gray-200">
                <div className="flex items-center gap-4">
                  <div className={`p-3 rounded-xl bg-${stat.color}-50`}>
                    <stat.icon className={`w-6 h-6 text-${stat.color}-600`} />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">{stat.label}</p>
                    <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {quickActions.map((action, idx) => (
              <div
                key={idx}
                onClick={() => navigateTo(action.mode as ViewMode)}
                className="bg-white rounded-2xl shadow-sm p-6 border border-gray-200 cursor-pointer hover:shadow-md transition-all group"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="p-3 rounded-xl bg-purple-50 group-hover:bg-purple-100 transition-colors">
                    <action.icon className="w-6 h-6 text-purple-600" />
                  </div>
                  <Plus className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-1">{action.label}</h3>
                <p className="text-gray-600 text-sm">{action.desc}</p>
              </div>
            ))}
          </div>

          <div className="mt-8 bg-white rounded-2xl shadow-sm p-6 border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">最近课程</h3>
            {courses.slice(0, 4).map((course) => (
              <div key={course.id} className="flex items-center justify-between py-4 border-b last:border-0">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600 font-bold">
                    {course.name.charAt(0)}
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{course.name}</p>
                    <p className="text-sm text-gray-600">{course.levels?.length || 0} 个关卡</p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setSelectedCourse(course);
                    navigateTo('editor');
                  }}
                  className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                >
                  管理
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {viewMode === 'import' && (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <button
              onClick={() => navigateTo('dashboard')}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>返回工作台</span>
            </button>
            <h1 className="text-2xl font-bold text-gray-900">AI 内容导入</h1>
            <p className="text-gray-600 mt-2">上传培训文档，AI 自动生成游戏化关卡</p>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="space-y-6">
                <CourseSelector
                  selectedCourse={selectedCourse}
                  onSelectCourse={setSelectedCourse}
                />
                <FileUploader
                  courseId={selectedCourse?.id || null}
                  onUpload={handleImport}
                />
              </div>
              <div>
                <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl p-6 mb-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <Sparkles className="w-6 h-6 text-purple-600" />
                    </div>
                    <h3 className="font-semibold text-gray-900">AI 智能处理</h3>
                  </div>
                  <ul className="space-y-2 text-sm text-gray-700">
                    <li className="flex items-start gap-2">
                      <span className="text-purple-600 mt-0.5">✓</span>
                      <span>自动提取知识要点</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-purple-600 mt-0.5">✓</span>
                      <span>生成多种题型题目</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-purple-600 mt-0.5">✓</span>
                      <span>创建关卡剧情和任务</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-purple-600 mt-0.5">✓</span>
                      <span>智能 NPC 对话配置</span>
                    </li>
                  </ul>
                </div>

                <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
                  <div className={`w-3 h-3 rounded-full ${aiStatus?.api_configured ? 'bg-green-500' : 'bg-yellow-500'}`} />
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      AI 服务状态：{aiStatus?.api_configured ? '就绪' : '需要配置'}
                    </p>
                    <p className="text-xs text-gray-600">
                      {aiStatus?.api_configured ? '可以使用完整功能' : '使用模拟数据，功能受限'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {jobId && (
            <ProgressStatus jobId={jobId} />
          )}
        </div>
      )}

      {viewMode === 'editor' && selectedCourse && (
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <button
              onClick={() => navigateTo('dashboard')}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>返回工作台</span>
            </button>
            <h1 className="text-2xl font-bold text-gray-900">{selectedCourse.name}</h1>
            <p className="text-gray-600 mt-2">管理课程关卡和题目</p>
          </div>
          <LevelEditor onSave={(data) => console.log('Save:', data)} onPreview={(data) => console.log('Preview:', data)} />
        </div>
      )}

      {viewMode === 'courses' && (
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <button
              onClick={() => navigateTo('dashboard')}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>返回工作台</span>
            </button>
            <h1 className="text-2xl font-bold text-gray-900">课程管理</h1>
            <p className="text-gray-600 mt-2">管理所有培训课程</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {courses.map((course) => (
              <div
                key={course.id}
                className="bg-white rounded-2xl shadow-sm overflow-hidden border border-gray-200 hover:shadow-md transition-all"
              >
                <div className="h-32 bg-gradient-to-br from-blue-500 to-purple-600" />
                <div className="p-6">
                  <h3 className="font-bold text-lg text-gray-900 mb-2">{course.name}</h3>
                  <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                    {course.description || '暂无描述'}
                  </p>
                  <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
                    <span>{course.levels?.length || 0} 个关卡</span>
                  </div>
                  <div className="flex gap-3">
                    <button
                      onClick={() => {
                        setSelectedCourse(course);
                        navigateTo('editor');
                      }}
                      className="flex-1 py-2 px-4 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors"
                    >
                      编辑
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {viewMode === 'analytics' && (
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <button
              onClick={() => navigateTo('dashboard')}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>返回工作台</span>
            </button>
            <h1 className="text-2xl font-bold text-gray-900">数据分析</h1>
            <p className="text-gray-600 mt-2">查看学员学习数据和课程表现</p>
          </div>
          <div className="grid grid-cols-1 gap-6">
            <div className="bg-white rounded-2xl shadow-sm p-6 border border-gray-200">
              <div className="text-center py-12 text-gray-500">
                <TrendingUp className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p>数据分析功能即将推出</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {viewMode === 'aiconfig' && (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <button
              onClick={() => navigateTo('dashboard')}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>返回工作台</span>
            </button>
            <h1 className="text-2xl font-bold text-gray-900">AI 配置</h1>
            <p className="text-gray-600 mt-2">配置 AI API 密钥以启用智能功能</p>
          </div>
          <AIConfigPanel onClose={() => navigateTo('dashboard')} />
        </div>
      )}
    </div>
  );
};


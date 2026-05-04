import React, { useState, useRef } from 'react';
import { Upload, CheckCircle, XCircle, RefreshCw, FileText, Bot, Settings, Sparkles } from 'lucide-react';
import { api, getCourses, contentAPI } from '../api';

interface CourseSelectorProps {
  selectedCourse: any;
  onSelectCourse: (course: any) => void;
}

export const CourseSelector: React.FC<CourseSelectorProps> = ({ selectedCourse, onSelectCourse }) => {
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  React.useEffect(() => {
    const fetchCourses = async () => {
      try {
        const data = await getCourses();
        setCourses(data);
      } catch (e) {
        console.error('Failed to fetch courses', e);
      } finally {
        setLoading(false);
      }
    };
    fetchCourses();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-500">
        <RefreshCw className="w-4 h-4 animate-spin" />
        <span>加载课程...</span>
      </div>
    );
  }

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">选择课程</label>
      <select
        value={selectedCourse?.id || ''}
        onChange={(e) => {
          const course = courses.find(c => c.id.toString() === e.target.value);
          if (course) onSelectCourse(course);
        }}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      >
        <option value="">请选择课程...</option>
        {courses.map(course => (
          <option key={course.id} value={course.id}>
            {course.name}
          </option>
        ))}
      </select>
    </div>
  );
};

interface FileUploaderProps {
  onUpload: (file: File, courseId: number) => Promise<string>;
  courseId: number | null;
}

export const FileUploader: React.FC<FileUploaderProps> = ({ onUpload, courseId }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !courseId) return;
    setIsUploading(true);
    try {
      await onUpload(selectedFile, courseId);
      setSelectedFile(null);
    } finally {
      setIsUploading(false);
    }
  };

  const supportedFormats = ['pdf', 'ppt', 'pptx', 'docx', 'txt'];
  const isSupported = selectedFile ? supportedFormats.includes(selectedFile.name.split('.').pop()?.toLowerCase() || '') : true;

  return (
    <div className="space-y-4">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all duration-200
          ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'}
          ${selectedFile && !isSupported ? 'border-red-300 bg-red-50' : ''}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.ppt,.pptx,.docx,.txt"
          onChange={handleFileSelect}
          className="hidden"
        />
        {selectedFile ? (
          <div className="space-y-2">
            <FileText className="w-12 h-12 mx-auto text-blue-600" />
            <div>
              <p className="font-medium text-gray-900">{selectedFile.name}</p>
              <p className="text-sm text-gray-500">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
            {!isSupported && (
              <p className="text-sm text-red-600">不支持的文件格式</p>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            <Upload className="w-12 h-12 mx-auto text-gray-400" />
            <div>
              <p className="font-medium text-gray-900">拖放文件到这里，或点击选择</p>
              <p className="text-sm text-gray-500">
                支持 PDF、PPT、DOCX、TXT 格式
              </p>
            </div>
          </div>
        )}
      </div>

      {selectedFile && isSupported && (
        <button
          onClick={handleUpload}
          disabled={!courseId || isUploading}
          className={`
            w-full py-3 px-4 rounded-lg font-medium text-white transition-all
            ${!courseId || isUploading ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}
          `}
        >
          {isUploading ? (
            <div className="flex items-center justify-center gap-2">
              <RefreshCw className="w-5 h-5 animate-spin" />
              <span>上传并处理中...</span>
            </div>
          ) : (
            <div className="flex items-center justify-center gap-2">
              <Sparkles className="w-5 h-5" />
              <span>上传并 AI 生成关卡</span>
            </div>
          )}
        </button>
      )}
    </div>
  );
};

interface ProgressStatusProps {
  jobId: string | null;
}

export const ProgressStatus: React.FC<ProgressStatusProps> = ({ jobId }) => {
  const [status, setStatus] = useState<any>(null);

  React.useEffect(() => {
    if (!jobId) return;

    const checkStatus = async () => {
      try {
        const data = await contentAPI.getImportStatus(jobId);
        setStatus(data);
        if (data.status !== 'completed' && data.status !== 'error') {
          setTimeout(checkStatus, 2000);
        }
      } catch (e) {
        console.error('Failed to check status', e);
      }
    };

    checkStatus();
  }, [jobId]);

  if (!jobId) return null;

  const steps = [
    { key: 'pending', label: '等待中', icon: '⏳' },
    { key: 'parsing', label: '解析文档', icon: '📄' },
    { key: 'processing', label: 'AI 处理', icon: '🤖' },
    { key: 'completed', label: '完成', icon: '✅' },
    { key: 'error', label: '出错', icon: '❌' },
  ];

  const currentStepIndex = steps.findIndex(s => s.key === status?.status);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">处理进度</h3>
      
      <div className="mb-6">
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>进度</span>
          <span>{status?.progress || 0}%</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
            style={{ width: `${status?.progress || 0}%` }}
          />
        </div>
      </div>

      <div className="space-y-3">
        {steps.slice(0, 4).map((step, idx) => (
          <div key={step.key} className="flex items-center gap-3">
            <div className={`
              w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
              ${idx < currentStepIndex ? 'bg-green-500 text-white' : 
                idx === currentStepIndex ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-500'}
            `}>
              {idx < currentStepIndex ? <CheckCircle className="w-4 h-4" /> : step.icon}
            </div>
            <span className={`${idx < currentStepIndex ? 'text-gray-900 font-medium' : 
              idx === currentStepIndex ? 'text-blue-600 font-medium' : 'text-gray-500'}`}>
              {step.label}
            </span>
          </div>
        ))}
      </div>

      {status?.status === 'completed' && (
        <div className="mt-6 p-4 bg-green-50 rounded-lg border border-green-200">
          <div className="flex items-center gap-2 text-green-700">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">关卡生成完成！</span>
          </div>
          <p className="mt-2 text-sm text-green-600">
            已成功导入并生成课程关卡，可以进入游戏学习了。
          </p>
        </div>
      )}

      {status?.status === 'error' && (
        <div className="mt-6 p-4 bg-red-50 rounded-lg border border-red-200">
          <div className="flex items-center gap-2 text-red-700">
            <XCircle className="w-5 h-5" />
            <span className="font-medium">处理失败</span>
          </div>
          <p className="mt-2 text-sm text-red-600">
            {status.message}
          </p>
        </div>
      )}
    </div>
  );
};

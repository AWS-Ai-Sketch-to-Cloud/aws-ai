import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import PageMeta from "../../components/common/PageMeta";
import {
  decodeSocialPayload,
  decodeSocialSignupPayload,
  saveAuthSession,
  type SocialSignupPayload,
} from "../../lib/auth-session";
import { getApiErrorMessage } from "../../lib/api-error";
import { toast } from "../../hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://127.0.0.1:8000";

type LoginResponse = {
  user: {
    userId: string;
    loginId: string;
    email: string;
    displayName: string;
    role: string;
  };
  accessToken: string;
  refreshToken: string;
};

export default function SocialCallbackPage() {
  const navigate = useNavigate();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [signupPayload, setSignupPayload] = useState<SocialSignupPayload | null>(null);
  const [isContinuing, setIsContinuing] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const payload = params.get("payload");
    const error = params.get("error");
    const signup = params.get("signup");

    if (signup) {
      try {
        setSignupPayload(decodeSocialSignupPayload(signup));
        return;
      } catch (error) {
        setErrorMessage(
          error instanceof Error
            ? error.message
            : "회원가입 안내 정보를 불러오지 못했습니다.",
        );
        return;
      }
    }

    if (error) {
      setErrorMessage(error);
      toast({
        title: "소셜 로그인 실패",
        description: error,
        variant: "destructive",
      });
      return;
    }

    if (!payload) {
      setErrorMessage("소셜 로그인 결과를 찾을 수 없습니다.");
      return;
    }

    try {
      const decoded = decodeSocialPayload(payload);
      saveAuthSession({
        user: decoded.user,
        accessToken: decoded.accessToken,
        refreshToken: decoded.refreshToken,
        apiBaseUrl: API_BASE_URL,
        authProvider: decoded.provider as
          | "github"
          | "google"
          | "kakao"
          | "naver",
      });

      toast({
        title: "로그인 완료",
        description: `${decoded.provider.toUpperCase()} 계정으로 로그인했습니다.`,
        variant: "success",
      });
      navigate("/dashboard", { replace: true });
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "소셜 로그인 결과를 처리하지 못했습니다.",
      );
    }
  }, [navigate]);

  const continueWithSignup = async () => {
    if (!signupPayload) {
      return;
    }

    setIsContinuing(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/social/complete-signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(signupPayload),
      });
      const body = (await res.json().catch(() => ({}))) as LoginResponse | unknown;

      if (!res.ok) {
        throw new Error(getApiErrorMessage(body, "자동 회원가입 처리에 실패했습니다."));
      }

      const login = body as LoginResponse;
      saveAuthSession({
        user: login.user,
        accessToken: login.accessToken,
        refreshToken: login.refreshToken,
        apiBaseUrl: API_BASE_URL,
        authProvider: signupPayload.provider as
          | "github"
          | "google"
          | "kakao"
          | "naver",
      });

      toast({
        title: "가입 및 로그인 완료",
        description: "바로 서비스를 이용할 수 있습니다.",
        variant: "success",
      });
      navigate("/dashboard", { replace: true });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "자동 회원가입 처리 중 오류가 발생했습니다.";
      setErrorMessage(message);
      toast({
        title: "자동 회원가입 실패",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsContinuing(false);
    }
  };

  const goBackToLogin = () => {
    navigate("/", { replace: true });
  };

  return (
    <>
      <PageMeta
        title="소셜 로그인 처리 중 | Sketch-to-Cloud"
        description="Sketch-to-Cloud 소셜 로그인 콜백"
      />
      <div className="relative min-h-screen overflow-hidden bg-[#FDFDFD] px-6 py-10 text-[#202020] dark:bg-[#0f172a] dark:text-slate-100">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,153,0,0.18),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(73,205,223,0.18),_transparent_28%)]" />
        <div className="relative mx-auto flex min-h-[calc(100vh-5rem)] max-w-3xl items-center justify-center">
          <section className="w-full rounded-3xl border border-[#E7E7E7] bg-white px-8 py-10 text-center shadow-2xl shadow-[#49CDDF]/10 backdrop-blur dark:border-slate-800 dark:bg-[#152238]">
            <h1 className="text-3xl font-semibold">
              {errorMessage ? "로그인에 실패했습니다." : "소셜 로그인 처리 중입니다."}
            </h1>
            <p className="mt-4 text-sm leading-6 text-gray-500 dark:text-slate-300">
              {errorMessage
                ? errorMessage
                : signupPayload
                  ? "가입 여부를 확인하고 있습니다."
                  : "잠시만 기다리면 다음 단계로 이동합니다."}
            </p>
          </section>
        </div>
      </div>

      <Dialog open={Boolean(signupPayload)}>
        <DialogContent
          showCloseButton={false}
          className="rounded-3xl border border-[#E7E7E7] bg-white p-8 dark:border-slate-800 dark:bg-[#152238]"
        >
          <DialogHeader className="text-left">
            <DialogTitle className="text-2xl font-semibold text-[#202020] dark:text-slate-50">
              이 계정으로 계속 진행할까요?
            </DialogTitle>
            <DialogDescription className="mt-2 text-sm leading-6 text-gray-600 dark:text-slate-300">
              아직 등록되지 않은 {signupPayload?.provider.toUpperCase()} 계정입니다.
              계속 진행하면 이 정보로 자동 가입 후 바로 로그인합니다.
            </DialogDescription>
          </DialogHeader>

          <div className="rounded-2xl border border-[#E7E7E7] bg-[#FAFAFA] px-4 py-4 text-sm text-gray-700 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-200">
            <p>이메일: {signupPayload?.email || "미제공"}</p>
            <p className="mt-2">표시 이름: {signupPayload?.displayName || "미제공"}</p>
          </div>

          <DialogFooter className="mt-2">
            <button
              type="button"
              onClick={goBackToLogin}
              disabled={isContinuing}
              className="inline-flex h-12 items-center justify-center rounded-xl border border-gray-200 px-4 text-sm font-semibold text-gray-700 transition hover:border-gray-300 disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:border-slate-500"
            >
              아니요, 돌아가기
            </button>
            <button
              type="button"
              onClick={continueWithSignup}
              disabled={isContinuing}
              className="inline-flex h-12 items-center justify-center rounded-xl bg-[#FF9900] px-4 text-sm font-semibold text-white transition hover:bg-[#e68a00] disabled:opacity-60"
            >
              {isContinuing ? "처리 중..." : "네, 계속 진행"}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { ArrowRight, CheckCircle2, Cloud, LoaderCircle, UserRoundPlus } from "lucide-react";
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
      } catch (err) {
        setErrorMessage(err instanceof Error ? err.message : "회원가입 안내 정보를 불러오지 못했습니다.");
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
      });

      toast({
        title: "로그인 완료",
        description: `${decoded.provider.toUpperCase()} 계정으로 로그인했습니다.`,
        variant: "success",
      });
      navigate("/workspace", { replace: true });
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "소셜 로그인 결과를 처리하지 못했습니다.",
      );
    }
  }, [navigate]);

  const continueWithSignup = async () => {
    if (!signupPayload) return;
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
      });
      toast({
        title: "가입 및 로그인 완료",
        description: "이제 바로 서비스를 사용할 수 있습니다.",
        variant: "success",
      });
      navigate("/workspace", { replace: true });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "자동 회원가입 처리 중 오류가 발생했습니다.";
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

  return (
    <>
      <PageMeta
        title="소셜 로그인 처리 중 | Sketch-to-Cloud"
        description="Sketch-to-Cloud 소셜 로그인 콜백 페이지"
      />
      <div className="relative min-h-screen overflow-hidden bg-[linear-gradient(180deg,#f7fbff_0%,#ecf3ff_100%)] px-6 py-10 text-[#122033]">
        <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-3xl items-center justify-center">
          <section className="w-full rounded-[2rem] border border-white/70 bg-white/88 px-8 py-10 text-center shadow-[0_24px_80px_rgba(72,123,255,0.14)] backdrop-blur">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-[#edf3ff] text-[#487bff]">
              {errorMessage ? <Cloud className="h-7 w-7" /> : <LoaderCircle className="h-7 w-7 animate-spin" />}
            </div>
            <h1 className="mt-6 text-3xl font-semibold">
              {errorMessage ? "로그인 처리에 실패했습니다." : "소셜 로그인 정보를 확인하는 중입니다."}
            </h1>
            <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-[#65748b]">
              {errorMessage
                ? errorMessage
                : signupPayload
                  ? "가입 가능 여부를 확인하고 있습니다."
                  : "잠시만 기다리면 다음 단계로 자동 이동합니다."}
            </p>
          </section>
        </div>
      </div>

      <Dialog open={Boolean(signupPayload)}>
        <DialogContent showCloseButton={false}>
          <DialogHeader className="text-left">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#edf3ff] text-[#487bff]">
              <UserRoundPlus className="h-6 w-6" />
            </div>
            <DialogTitle className="pt-4">이 계정으로 계속 진행할까요?</DialogTitle>
            <DialogDescription>
              아직 등록되지 않은 {signupPayload?.provider.toUpperCase()} 계정입니다.
              계속 진행하면 현재 정보로 자동 가입 후 바로 로그인합니다.
            </DialogDescription>
          </DialogHeader>

          <div className="rounded-[1.5rem] border border-[#d9e4f2] bg-[#f8fbff] px-4 py-4 text-sm text-[#314257]">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-[#58e1c1]" />
              <p>이메일: {signupPayload?.email || "미제공"}</p>
            </div>
            <div className="mt-2 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-[#58e1c1]" />
              <p>표시 이름: {signupPayload?.displayName || "미제공"}</p>
            </div>
          </div>

          <DialogFooter className="mt-2">
            <button
              type="button"
              onClick={() => navigate("/login", { replace: true })}
              disabled={isContinuing}
              className="inline-flex h-12 items-center justify-center rounded-2xl border border-[#d9e4f2] bg-white px-4 text-sm font-semibold text-[#314257] transition hover:border-[#487bff] hover:text-[#487bff] disabled:opacity-60"
            >
              돌아가기
            </button>
            <button
              type="button"
              onClick={continueWithSignup}
              disabled={isContinuing}
              className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-[#122033] px-4 text-sm font-semibold text-white transition hover:bg-[#1b2c44] disabled:opacity-60"
            >
              {isContinuing ? "처리 중..." : "계속 진행"}
              {!isContinuing ? <ArrowRight className="h-4 w-4" /> : null}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
